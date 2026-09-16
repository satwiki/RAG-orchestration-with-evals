"""LangGraph multi-agent e-commerce analytics workflow.

Pipeline: intent_detector -> query_generator -> query_validator -> executor
-> report_builder, with report_builder able to loop back to query_generator
for deeper analysis (capped at MAX_TURNS) and query_validator able to loop
back to query_generator on syntax errors (capped at MAX_VALIDATION_RETRIES).
"""

from __future__ import annotations

import os
from functools import cache, lru_cache
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import AzureChatOpenAI, ChatOpenAI
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field
from state import AgentState, QueryRecord
from tools import execute_readonly_query, get_current_datetime
from utils.db import validate_sql_syntax

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

MAX_VALIDATION_RETRIES = 3
MAX_TURNS = 5

_PROMPTS_PATH = Path(__file__).resolve().parents[1] / "prompts"
_SCHEMA_PATH = Path(__file__).resolve().parents[1] / "skills" / "ecommerce-db-schema.md"

_QUERY_GENERATOR_PROMPT_TEMPLATE = "{system_prompt}\n\nDatabase schema:\n{schema}"
_REPORT_BUILDER_PROMPT_TEMPLATE = "{system_prompt}\n\n{forced_final_note}"

_FORCED_FINAL_NOTE = (
    "The turn limit has been reached: no more queries are allowed. You must set needs_more_data to "
    "false and produce the best possible final answer with the data gathered so far, noting any gaps."
)


@cache
def _load_system_prompt(name: str) -> str:
    """Read a raw system prompt from the shared prompts directory."""
    return (_PROMPTS_PATH / f"{name}.md").read_text(encoding="utf-8").strip()


INTENT_SYSTEM_PROMPT = _load_system_prompt("intent-detector")
QUERY_GENERATOR_SYSTEM_PROMPT = _load_system_prompt("query-generator")
REPORT_BUILDER_SYSTEM_PROMPT = _load_system_prompt("report-builder")
TEMPORAL_GUIDANCE_PROMPT = _load_system_prompt("temporal-guidance")


class IntentDecision(BaseModel):
    """Gatekeeper decision on whether a user question may proceed."""

    allowed: bool = Field(
        description="True if the question can be answered via a read-only analytics query."
    )
    reason: str = Field(
        description="Short explanation for the decision, especially when blocked."
    )


class GeneratedQuery(BaseModel):
    """A single generated SQL statement."""

    sql: str = Field(
        description="A single SQLite SELECT statement. No markdown fences, no commentary."
    )


class ReportDecision(BaseModel):
    """Report builder's grounded answer and continuation decision."""

    needs_more_data: bool = Field(
        description="True if another SQL query is required to fully answer the question."
    )
    follow_up_instructions: str = Field(
        default="",
        description="What additional data the next query should gather, if needs_more_data is true.",
    )
    answer_markdown: str = Field(
        description="The grounded answer in markdown, including a data table when relevant."
    )


@lru_cache(maxsize=1)
def _load_schema_skill() -> str:
    """Read the e-commerce schema skill markdown used to ground SQL generation."""
    return _SCHEMA_PATH.read_text(encoding="utf-8")


def _normalize_azure_endpoint(endpoint: str) -> str:
    """Strip whitespace and a trailing slash from an Azure / Foundry endpoint URL."""
    return endpoint.strip().rstrip("/")


def _uses_foundry_v1(endpoint: str) -> bool:
    """Return True when the endpoint is an Azure AI Foundry Models v1 base URL."""
    return _normalize_azure_endpoint(endpoint).endswith("/openai/v1")


@lru_cache(maxsize=1)
def _get_llm() -> AzureChatOpenAI | ChatOpenAI:
    """Build the chat client used by every node, created lazily on first use.

    Foundry v1 bases (`.../openai/v1`) must use ChatOpenAI against
    `/openai/v1/chat/completions`. AzureChatOpenAI would append
    `/openai/deployments/{name}/chat/completions` and 404.
    """
    endpoint = _normalize_azure_endpoint(os.environ["AZURE_AI_FOUNDRY_ENDPOINT"])
    deployment = os.environ.get("AZURE_AI_FOUNDRY_DEPLOYMENT") or "gpt-5.4-nano"
    api_key = os.environ["AZURE_AI_FOUNDRY_API_KEY"]
    if _uses_foundry_v1(endpoint):
        return ChatOpenAI(base_url=endpoint, api_key=api_key, model=deployment)
    return AzureChatOpenAI(
        azure_endpoint=endpoint,
        azure_deployment=deployment,
        api_key=api_key,
        api_version=os.environ.get("AZURE_OPENAI_API_VERSION", "2024-12-01-preview"),
        temperature=0,
    )


def _resolve_question(state: AgentState) -> str:
    """Pull the user question from state, falling back to the latest human message."""
    if state.get("user_question"):
        return state["user_question"]
    for message in reversed(state.get("messages") or []):
        content = getattr(message, "content", None)
        if content:
            return content
    return ""


def _render_temporal_prompt(
    current_datetime: str | None = None, *, is_evaluation: bool = False
) -> str:
    """Render temporal guidance using the runtime clock tool."""
    timestamp = current_datetime or get_current_datetime.invoke(
        {"is_evaluation": is_evaluation}
    )
    return TEMPORAL_GUIDANCE_PROMPT.format(current_datetime=timestamp)


def _summarize_history(history: list[QueryRecord]) -> str:
    """Render all executed query results as plain text for LLM grounding."""
    if not history:
        return "No queries executed yet."
    lines: list[str] = []
    for i, record in enumerate(history, start=1):
        lines.append(f"Query {i}: {record.get('sql')}")
        if record.get("error"):
            lines.append(f"  Error: {record['error']}")
        else:
            rows = record.get("rows") or []
            lines.append(f"  Rows returned: {len(rows)}")
            lines.append(f"  Rows: {rows}")
    return "\n".join(lines)


def intent_detector(state: AgentState) -> dict[str, Any]:
    """Classify the user question as allowed or blocked before any SQL is generated."""
    question = _resolve_question(state)
    messages: list[Any] = [
        SystemMessage(content=INTENT_SYSTEM_PROMPT),
        HumanMessage(content=question),
    ]
    if state.get("task_context"):
        messages.append(
            HumanMessage(
                content=f"Task-specific requirements:\n{state['task_context']}"
            )
        )
    decision = _get_llm().with_structured_output(IntentDecision).invoke(messages)
    explicit_write = any(
        keyword in question.lower()
        for keyword in (
            "insert ",
            "update ",
            "delete ",
            "drop ",
            "alter ",
            "create table",
            "modify data",
        )
    )
    blocked = not decision.allowed and (explicit_write or not state.get("task_context"))
    update: dict[str, Any] = {
        "user_question": question,
        "intent": "blocked" if blocked else "allowed",
        "intent_reason": decision.reason,
        "blocked": blocked,
    }
    if blocked:
        update["final_answer"] = f"I can't help with that request. {decision.reason}"
    return update


def query_generator(state: AgentState) -> dict[str, Any]:
    """Generate a SQL statement, incorporating prior history, follow-up asks, or validator feedback."""
    prompt: list[Any] = [
        SystemMessage(
            content=_QUERY_GENERATOR_PROMPT_TEMPLATE.format(
                system_prompt=QUERY_GENERATOR_SYSTEM_PROMPT,
                schema=_load_schema_skill(),
            )
        ),
        HumanMessage(
            content=_render_temporal_prompt(
                is_evaluation=bool(state.get("is_evaluation"))
            )
        ),
        HumanMessage(content=f"User question: {state['user_question']}"),
    ]
    if state.get("task_context"):
        prompt.append(
            HumanMessage(
                content=f"Task-specific requirements:\n{state['task_context']}"
            )
        )
    if state.get("required_output_columns"):
        columns = ", ".join(state["required_output_columns"])
        prompt.append(HumanMessage(content=f"Required output columns: {columns}."))
    history = state.get("query_history") or []
    if history:
        prompt.append(
            HumanMessage(
                content=f"Previously executed queries:\n{_summarize_history(history)}"
            )
        )
    if state.get("follow_up_instructions"):
        prompt.append(
            HumanMessage(
                content=f"Additional data needed: {state['follow_up_instructions']}"
            )
        )
    if state.get("validation_feedback"):
        prompt.append(
            HumanMessage(
                content=f"The previous query was rejected: {state['validation_feedback']}. Fix it."
            )
        )
    result = _get_llm().with_structured_output(GeneratedQuery).invoke(prompt)
    return {"query": result.sql, "validation_feedback": None}


def query_validator(state: AgentState) -> dict[str, Any]:
    """Check the generated SQL is read-only and syntactically valid without executing it."""
    error = validate_sql_syntax(state["query"])
    if error is None:
        error = _validate_aggregation_contract(
            state["query"], state.get("task_context")
        )
    if error is None:
        return {"query_validation": [], "validation_feedback": None, "retry_count": 0}
    retry_count = (state.get("retry_count") or 0) + 1
    return {
        "query_validation": [error],
        "validation_feedback": error,
        "retry_count": retry_count,
    }


def _validate_aggregation_contract(sql: str, task_context: str | None) -> str | None:
    """Reject order-total joins that would multiply header values by line items."""
    if not task_context or "order totals at order grain" not in task_context.lower():
        return None
    normalized = " ".join(sql.lower().split())
    select_blocks = normalized.split(" select ")[1:]
    for block in select_blocks:
        block = block.split(" select ", 1)[0]
        if "sum(o.total_amount)" in block and "join order_items" in block:
            return (
                "Aggregate orders.total_amount in an order-level CTE before joining order_items; "
                "never sum order totals in the same SELECT block as raw line items."
            )
    return None


def _route_after_validation(state: AgentState) -> str:
    """Route to the executor, back to the generator for a retry, or give up after too many retries."""
    if not state.get("validation_feedback"):
        return "executor"
    if (state.get("retry_count") or 0) >= MAX_VALIDATION_RETRIES:
        return "give_up"
    return "query_generator"


def record_query_failure(state: AgentState) -> dict[str, Any]:
    """Record a query that never passed validation so the report builder can still respond."""
    history = list(state.get("query_history") or [])
    history.append(
        {
            "sql": state.get("query"),
            "rows": None,
            "error": state.get("validation_feedback"),
        }
    )
    return {
        "query_history": history,
        "turn_count": (state.get("turn_count") or 0) + 1,
        "query_result": None,
        "retry_count": 0,
        "validation_feedback": None,
    }


def executor(state: AgentState) -> dict[str, Any]:
    """Run the validated read-only query and append the outcome to query history."""
    history = list(state.get("query_history") or [])
    turn_count = (state.get("turn_count") or 0) + 1
    try:
        rows = execute_readonly_query.invoke({"sql": state["query"]})
        history.append({"sql": state["query"], "rows": rows, "error": None})
        return {
            "query_result": rows,
            "query_history": history,
            "turn_count": turn_count,
            "error": None,
        }
    except Exception as exc:  # noqa: BLE001 - surfaced to report_builder, not raised
        history.append({"sql": state["query"], "rows": None, "error": str(exc)})
        return {
            "query_result": None,
            "query_history": history,
            "turn_count": turn_count,
            "error": str(exc),
        }


def report_builder(state: AgentState) -> dict[str, Any]:
    """Synthesize a grounded markdown answer and decide whether another query turn is warranted."""
    turn_count = state.get("turn_count") or 0
    forced_final = turn_count >= MAX_TURNS
    prompt = [
        SystemMessage(
            content=_REPORT_BUILDER_PROMPT_TEMPLATE.format(
                system_prompt=REPORT_BUILDER_SYSTEM_PROMPT,
                forced_final_note=_FORCED_FINAL_NOTE if forced_final else "",
            ).rstrip()
        ),
        HumanMessage(
            content=_render_temporal_prompt(
                is_evaluation=bool(state.get("is_evaluation"))
            )
        ),
        HumanMessage(content=f"User question: {state['user_question']}"),
        HumanMessage(
            content=f"Query history:\n{_summarize_history(state.get('query_history') or [])}"
        ),
    ]
    if state.get("task_context"):
        prompt.insert(
            2,
            HumanMessage(
                content=f"Task-specific requirements:\n{state['task_context']}"
            ),
        )
    if state.get("required_output_columns"):
        columns = ", ".join(state["required_output_columns"])
        prompt.insert(3, HumanMessage(content=f"Required output columns: {columns}."))
    decision = _get_llm().with_structured_output(ReportDecision).invoke(prompt)
    needs_more = bool(decision.needs_more_data) and not forced_final
    return {
        "final_answer": decision.answer_markdown,
        "needs_more_data": needs_more,
        "follow_up_instructions": decision.follow_up_instructions
        if needs_more
        else None,
    }


def _route_after_report(state: AgentState) -> str:
    """Loop back for another query turn, or end the workflow with the final answer."""
    return "query_generator" if state.get("needs_more_data") else "__end__"


def build_workflow() -> StateGraph:
    """Assemble the uncompiled multi-agent analytics workflow graph."""
    workflow = StateGraph(AgentState)
    workflow.add_node("intent_detector", intent_detector)
    workflow.add_node("query_generator", query_generator)
    workflow.add_node("query_validator", query_validator)
    workflow.add_node("executor", executor)
    workflow.add_node("record_query_failure", record_query_failure)
    workflow.add_node("report_builder", report_builder)

    workflow.add_edge(START, "intent_detector")
    workflow.add_conditional_edges(
        "intent_detector",
        lambda state: "__end__" if state.get("blocked") else "query_generator",
        {"query_generator": "query_generator", "__end__": END},
    )
    workflow.add_edge("query_generator", "query_validator")
    workflow.add_conditional_edges(
        "query_validator",
        _route_after_validation,
        {
            "executor": "executor",
            "query_generator": "query_generator",
            "give_up": "record_query_failure",
        },
    )
    workflow.add_edge("executor", "report_builder")
    workflow.add_edge("record_query_failure", "report_builder")
    workflow.add_conditional_edges(
        "report_builder",
        _route_after_report,
        {"query_generator": "query_generator", "__end__": END},
    )
    return workflow


@lru_cache(maxsize=1)
def get_compiled_agent():
    """Compile and cache the single shared graph instance."""
    return build_workflow().compile()


agent = get_compiled_agent()


def ask(question: str) -> str:
    """Run the workflow for a user question and return the final markdown answer."""
    result = agent.invoke(
        {
            "user_question": question,
            "messages": [HumanMessage(content=question)],
        }
    )
    return result.get("final_answer", "")

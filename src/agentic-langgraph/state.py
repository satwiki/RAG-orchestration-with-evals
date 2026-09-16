"""Agent state definitions for the LangGraph e-commerce analytics workflow."""

from __future__ import annotations

from typing import Annotated, Any

from langgraph.graph.message import add_messages
from typing_extensions import TypedDict


class QueryRecord(TypedDict, total=False):
    """A single generated SQL query and the outcome of executing it."""

    sql: str
    rows: list[dict[str, Any]] | None
    error: str | None


class AgentState(TypedDict, total=False):
    """Represents agent state in the LangGraph framework.

    Core fields are shared across nodes. Optional routing and reporting fields
    support the multi-agent analytics workflow.
    """

    # Conversation and shared workflow fields
    messages: Annotated[list[Any], add_messages]
    query: str | None
    query_validation: list[str] | None
    query_result: Any | None
    user_question: str | None
    is_evaluation: bool | None
    task_context: str | None
    required_output_columns: list[str] | None
    intent: str | None
    intent_reason: str | None
    blocked: bool | None
    validation_feedback: str | None
    retry_count: int | None
    final_answer: str | None
    error: str | None
    # Multi-query analytics loop fields
    query_history: list[QueryRecord] | None
    turn_count: int | None
    needs_more_data: bool | None
    follow_up_instructions: str | None

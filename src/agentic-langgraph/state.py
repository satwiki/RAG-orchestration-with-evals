"""Agent state definitions for the LangGraph e-commerce analytics workflow."""

from __future__ import annotations

from typing import Any, Optional

from langgraph.graph.message import add_messages
from typing_extensions import TypedDict, Annotated


class QueryRecord(TypedDict, total=False):
    """A single generated SQL query and the outcome of executing it."""

    sql: str
    rows: Optional[list[dict[str, Any]]]
    error: Optional[str]


class AgentState(TypedDict, total=False):
    """Represents agent state in the LangGraph framework.

    Core fields are shared across nodes. Optional routing and reporting fields
    support the multi-agent analytics workflow.
    """
    # Conversation and shared workflow fields
    messages: Annotated[list[Any], add_messages]
    query: Optional[str]
    query_validation: Optional[list[str]]
    query_result: Optional[Any]
    user_question: Optional[str]
    intent: Optional[str]
    intent_reason: Optional[str]
    blocked: Optional[bool]
    validation_feedback: Optional[str]
    retry_count: Optional[int]
    final_answer: Optional[str]
    error: Optional[str]
    # Multi-query analytics loop fields
    query_history: Optional[list[QueryRecord]]
    turn_count: Optional[int]
    needs_more_data: Optional[bool]
    follow_up_instructions: Optional[str]

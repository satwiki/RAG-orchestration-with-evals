"""Deterministic tools for the LangGraph e-commerce analytics workflow."""

from __future__ import annotations

import os
from datetime import date, datetime, time, timezone
from typing import Any

from langchain_core.tools import tool

from utils.db import run_read_only_query


@tool
def get_current_datetime(is_evaluation: bool = False) -> str:
    """Return a real or evaluation date and time as an ISO 8601 timestamp.

    Args:
        is_evaluation: Use the frozen evaluation date instead of the real clock.

    Returns:
        An ISO 8601 timestamp with timezone information.

    Raises:
        ValueError: If evaluation mode is enabled without an evaluation date.
    """
    if is_evaluation:
        evaluation_date = os.environ.get("RAG_EVAL_AS_OF_DATE")
        if not evaluation_date:
            raise ValueError("RAG_EVAL_AS_OF_DATE is required in evaluation mode.")
        frozen_date = date.fromisoformat(evaluation_date)
        return datetime.combine(frozen_date, time.min, tzinfo=timezone.utc).isoformat()
    return datetime.now().astimezone().isoformat(timespec="seconds")


@tool
def execute_readonly_query(sql: str) -> list[dict[str, Any]]:
    """Execute a read-only SQL SELECT statement against the e-commerce database and return matching rows."""
    return run_read_only_query(sql)

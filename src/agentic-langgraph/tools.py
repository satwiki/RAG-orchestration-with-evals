"""Deterministic tools for the LangGraph e-commerce analytics workflow."""

from __future__ import annotations

from typing import Any

from langchain_core.tools import tool

from utils.db import run_read_only_query


@tool
def execute_readonly_query(sql: str) -> list[dict[str, Any]]:
    """Execute a read-only SQL SELECT statement against the e-commerce database and return matching rows."""
    return run_read_only_query(sql)

"""Compatibility imports for framework-neutral e-commerce database helpers."""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.utils.db import (
    QueryRejectedError,
    assert_read_only,
    get_db_path,
    run_read_only_query,
    validate_sql_syntax,
)

__all__ = [
    "QueryRejectedError",
    "assert_read_only",
    "get_db_path",
    "run_read_only_query",
    "validate_sql_syntax",
]

"""Read-only SQLite helpers shared across framework-specific agent code.

These helpers intentionally expose no write/DDL capability. Callers get a
single safe entry point for validating and executing analytics queries
against the local e-commerce database.
"""

from __future__ import annotations

import os
import re
import sqlite3
from pathlib import Path
from typing import Any

_FORBIDDEN_KEYWORDS = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|REPLACE|TRUNCATE|ATTACH|DETACH|PRAGMA|VACUUM)\b",
    re.IGNORECASE,
)
_DEFAULT_ROW_LIMIT = 200


class QueryRejectedError(ValueError):
    """Raised when a SQL statement fails the read-only safety check."""


def get_db_path() -> Path:
    """Resolve the e-commerce SQLite database path from env or the repo default location."""
    default_path = Path(__file__).resolve().parents[1] / "local_db" / "ecommerce" / "ecommerce.db"
    return Path(os.environ.get("ECOMMERCE_DB_PATH", default_path))


def assert_read_only(sql: str) -> None:
    """Raise QueryRejectedError unless `sql` is a single read-only SELECT/CTE statement."""
    statement = sql.strip().rstrip(";")
    if not statement:
        raise QueryRejectedError("Empty SQL statement.")
    if ";" in statement:
        raise QueryRejectedError("Only a single SQL statement is allowed.")
    if not re.match(r"^\s*(SELECT|WITH)\b", statement, re.IGNORECASE):
        raise QueryRejectedError("Only SELECT (or WITH ... SELECT) statements are allowed.")
    if _FORBIDDEN_KEYWORDS.search(statement):
        raise QueryRejectedError("Statement contains a disallowed write/DDL keyword.")


def validate_sql_syntax(sql: str, db_path: Path | None = None) -> str | None:
    """Check `sql` is read-only and syntactically valid without executing it. Returns an error message, or None."""
    try:
        assert_read_only(sql)
    except QueryRejectedError as exc:
        return str(exc)

    path = db_path or get_db_path()
    try:
        with sqlite3.connect(path) as conn:
            # EXPLAIN QUERY PLAN parses/plans the statement without reading data.
            conn.execute(f"EXPLAIN QUERY PLAN {sql.strip().rstrip(';')}")
        return None
    except sqlite3.Error as exc:
        return str(exc)


def run_read_only_query(
    sql: str, db_path: Path | None = None, row_limit: int = _DEFAULT_ROW_LIMIT
) -> list[dict[str, Any]]:
    """Execute a validated read-only SQL query and return rows as a list of dicts."""
    assert_read_only(sql)
    path = db_path or get_db_path()
    with sqlite3.connect(path) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.execute(sql.strip().rstrip(";"))
        rows = cursor.fetchmany(row_limit)
        return [dict(row) for row in rows]

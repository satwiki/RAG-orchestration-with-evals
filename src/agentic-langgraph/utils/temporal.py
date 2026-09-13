"""Calendar-boundary helpers for the LangGraph analytics workflow."""

from __future__ import annotations

from datetime import date


def calendar_quarter_number(as_of: date) -> int:
    """Return the 1-based calendar quarter that contains ``as_of``."""
    return (as_of.month - 1) // 3 + 1


def calendar_quarter_label(as_of: date) -> str:
    """Return a stable ``YYYY-Qn`` label for the calendar quarter of ``as_of``."""
    return f"{as_of.year}-Q{calendar_quarter_number(as_of)}"


def calendar_year_bounds(year: int) -> tuple[date, date]:
    """Return the inclusive start and exclusive end of a calendar year."""
    return date(year, 1, 1), date(year + 1, 1, 1)


def completed_quarter_bounds(as_of: date) -> tuple[date, date]:
    """Return the start and exclusive end of the last completed calendar quarter."""
    current_quarter = calendar_quarter_number(as_of) - 1
    current_quarter_start = date(as_of.year, current_quarter * 3 + 1, 1)
    previous_quarter_index = current_quarter - 1
    previous_quarter_year = as_of.year
    if previous_quarter_index < 0:
        previous_quarter_index = 3
        previous_quarter_year -= 1
    return (
        date(previous_quarter_year, previous_quarter_index * 3 + 1, 1),
        current_quarter_start,
    )


def sqlite_calendar_quarter_label_sql(date_column: str = "order_date") -> str:
    """Return parenthesized SQLite SQL that labels a date as ``YYYY-Qn``.

    SQLite ``||`` binds tighter than ``/`` and ``+``. Unparenthesized expressions
    such as ``year || '-Q' || (month - 1) / 3 + 1`` become numeric (often 676)
    instead of distinct quarter labels.
    """
    year_sql = f"CAST(strftime('%Y', {date_column}) AS TEXT)"
    month_sql = f"CAST(strftime('%m', {date_column}) AS INTEGER)"
    quarter_sql = f"CAST(((({month_sql}) - 1) / 3) + 1 AS TEXT)"
    return f"({year_sql} || '-Q' || {quarter_sql})"


def sqlite_calendar_quarter_sort_sql(date_column: str = "order_date") -> str:
    """Return parenthesized SQLite SQL that sorts calendar quarters chronologically."""
    year_sql = f"CAST(strftime('%Y', {date_column}) AS INTEGER)"
    month_sql = f"CAST(strftime('%m', {date_column}) AS INTEGER)"
    quarter_sql = f"(((({month_sql}) - 1) / 3) + 1)"
    return f"(({year_sql}) * 10 + {quarter_sql})"

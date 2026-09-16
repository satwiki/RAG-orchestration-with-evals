"""Normalized SQL result parsing and comparison for evaluation."""

from __future__ import annotations

import json
import math
import re
from typing import Any

_ORDER_BY = re.compile(r"\bORDER\s+BY\b", re.IGNORECASE)
_NUMERIC_STRING = re.compile(r"^-?\d+(\.\d+)?$")
_MONTH_VALUE = re.compile(r"^(\d{4}-\d{2})(?:-01)?$")
_NUMERIC_TOLERANCE = 0.01

_COLUMN_ALIASES = {
    "product_sku": "sku",
    "product_name": "name",
    "product_category": "category",
    "sales_amount": "product_revenue",
    "gross_sales_amount": "product_revenue",
    "delivered_order_revenue": "order_revenue",
}


def sql_requires_row_order(sql: str) -> bool:
    """Return True when ordering affects a ranked or descending result."""
    if _ORDER_BY.search(sql or "") is None:
        return False
    return bool(re.search(r"\bLIMIT\b|\bDESC\b", sql or "", re.IGNORECASE))


def parse_result_payload(payload: Any) -> list[dict[str, Any]]:
    """Parse a golden or live result into a list of row dictionaries."""
    if payload is None:
        return []
    if isinstance(payload, list):
        return [dict(row) for row in payload]
    if isinstance(payload, str):
        stripped = payload.strip()
        if not stripped:
            return []
        loaded = json.loads(stripped)
        if isinstance(loaded, list):
            return [dict(row) for row in loaded]
        raise ValueError("Result JSON must be a list of objects.")
    raise ValueError(f"Unsupported result payload type: {type(payload)!r}")


def _normalize_value(value: Any) -> Any:
    """Normalize a cell for comparison, including numeric tolerance."""
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, int) and not isinstance(value, bool):
        return float(value)
    if isinstance(value, float):
        if math.isnan(value):
            return None
        return round(value, 2)
    if isinstance(value, bytes):
        return value.decode("utf-8")
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.lower() in {"none", "null"}:
            return None
        if _NUMERIC_STRING.match(stripped):
            return round(float(stripped), 2)
        return stripped
    return value


def _canonicalize_row(row: dict[str, Any]) -> dict[str, Any]:
    """Normalize common semantic aliases while retaining required result fields."""
    canonical = {
        _COLUMN_ALIASES.get(str(key).lower(), str(key).lower()): _normalize_value(value)
        for key, value in row.items()
    }
    if (
        "customer_name" not in canonical
        and {"first_name", "last_name"} <= canonical.keys()
    ):
        canonical["customer_name"] = (
            f"{canonical['first_name']} {canonical['last_name']}"
        )
    return canonical


def normalize_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Lower-case keys and normalize cell values."""
    return [_canonicalize_row(row) for row in rows]


def _values_equal(left: Any, right: Any) -> bool:
    """Compare two normalized cell values with numeric tolerance."""
    if left is None or right is None:
        return left is right
    if isinstance(left, float) and isinstance(right, float):
        return math.isclose(left, right, abs_tol=_NUMERIC_TOLERANCE, rel_tol=0.0)
    if isinstance(left, str) and isinstance(right, str):
        left_month = _MONTH_VALUE.fullmatch(left)
        right_month = _MONTH_VALUE.fullmatch(right)
        if left_month and right_month:
            return left_month.group(1) == right_month.group(1)
    return left == right


def _rows_equal(left: dict[str, Any], right: dict[str, Any]) -> bool:
    """Compare two normalized rows, ignoring column order."""
    if set(left) != set(right):
        return False
    return all(_values_equal(left[key], right[key]) for key in left)


def results_equivalent(
    actual_rows: list[dict[str, Any]],
    expected_rows: list[dict[str, Any]],
    *,
    order_matters: bool,
) -> tuple[bool, str]:
    """Return whether two result sets match after normalization."""
    actual = normalize_rows(actual_rows)
    expected = normalize_rows(expected_rows)
    if len(actual) != len(expected):
        return (
            False,
            f"Row count mismatch: actual={len(actual)} expected={len(expected)}",
        )
    if not actual:
        return True, "Both results are empty."

    actual_columns = set(actual[0])
    expected_columns = set(expected[0])
    if not expected_columns <= actual_columns:
        missing = sorted(expected_columns - actual_columns)
        return False, f"Column mismatch: missing={missing}"
    if actual_columns != expected_columns:
        actual = [{key: row[key] for key in expected_columns} for row in actual]

    if order_matters:
        for index, (actual_row, expected_row) in enumerate(
            zip(actual, expected, strict=True)
        ):
            if not _rows_equal(actual_row, expected_row):
                return False, f"Row {index} differs after ORDER BY comparison."
        return True, "Rows match in order."

    unmatched = list(expected)
    for actual_row in actual:
        found_index = next(
            (
                index
                for index, expected_row in enumerate(unmatched)
                if _rows_equal(actual_row, expected_row)
            ),
            None,
        )
        if found_index is None:
            return (
                False,
                "A generated row has no matching gold row when order is ignored.",
            )
        unmatched.pop(found_index)
    return True, "Rows match regardless of order."

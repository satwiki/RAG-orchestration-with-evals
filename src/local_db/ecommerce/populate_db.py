#!/usr/bin/env python3
"""Create and populate a local SQLite e-commerce database with dummy data."""

from __future__ import annotations

import argparse
import logging
import sqlite3
import sys
from datetime import date
from pathlib import Path

from seed_data import (
    CategoryRecord,
    CustomerRecord,
    OrderRecord,
    ProductEngagementRecord,
    ProductRecord,
    build_rng,
    generate_categories,
    generate_customers,
    generate_orders,
    generate_product_engagement,
    generate_products,
    monthly_order_buckets,
    summarize_seed,
)

EXIT_SUCCESS = 0
EXIT_FAILURE = 1
EXIT_ERROR = 2

logger = logging.getLogger(__name__)

DEFAULT_DB_PATH = Path(__file__).resolve().parent / "ecommerce.db"
SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"


def configure_logging(verbose: bool = False) -> None:
    """Configure root logging for CLI usage."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=level, format="%(levelname)s: %(message)s")


def create_parser() -> argparse.ArgumentParser:
    """Create and configure the CLI argument parser."""
    parser = argparse.ArgumentParser(
        description=(
            "Create a local SQLite e-commerce database and populate it with "
            "deterministic dummy product, customer, multi-year order, and "
            "product engagement data."
        )
    )
    parser.add_argument(
        "--db-path",
        type=Path,
        default=DEFAULT_DB_PATH,
        help=f"Output SQLite database path (default: {DEFAULT_DB_PATH})",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducible dummy data (default: 42)",
    )
    parser.add_argument(
        "--products-per-category",
        type=int,
        default=20,
        help="Number of products to generate per category (default: 20)",
    )
    parser.add_argument(
        "--customers",
        type=int,
        default=120,
        help="Number of customers to generate (default: 120)",
    )
    parser.add_argument(
        "--orders",
        type=int,
        default=1800,
        help="Number of orders to generate across the history window (default: 1800)",
    )
    parser.add_argument(
        "--history-years",
        type=int,
        default=2,
        help="Number of years of order history to generate (minimum 2, default: 2)",
    )
    parser.add_argument(
        "--as-of-date",
        type=date.fromisoformat,
        default=None,
        help="Freeze generated catalog and history relative to YYYY-MM-DD (default: today).",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Delete and recreate the database file if it already exists",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable debug logging",
    )
    return parser


def validate_args(args: argparse.Namespace) -> None:
    """Validate CLI arguments before database work begins."""
    if args.products_per_category < 20:
        raise ValueError("--products-per-category must be at least 20")
    if args.customers < 1:
        raise ValueError("--customers must be at least 1")
    if args.orders < 1:
        raise ValueError("--orders must be at least 1")
    if args.history_years < 2:
        raise ValueError("--history-years must be at least 2")
    if not SCHEMA_PATH.is_file():
        raise FileNotFoundError(f"Schema file not found: {SCHEMA_PATH}")


def connect_database(db_path: Path) -> sqlite3.Connection:
    """Open a SQLite connection with foreign keys enabled."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(db_path)
    connection.execute("PRAGMA foreign_keys = ON")
    connection.row_factory = sqlite3.Row
    return connection


def apply_schema(connection: sqlite3.Connection, schema_path: Path = SCHEMA_PATH) -> None:
    """Apply the SQL schema to an open connection."""
    schema_sql = schema_path.read_text(encoding="utf-8")
    connection.executescript(schema_sql)
    connection.commit()
    logger.debug("Applied schema from %s", schema_path)


def clear_tables(connection: sqlite3.Connection) -> None:
    """Remove existing rows while preserving schema objects."""
    tables = [
        "product_engagement",
        "order_items",
        "orders",
        "products",
        "customers",
        "categories",
    ]
    for table in tables:
        connection.execute(f"DELETE FROM {table}")

    sequence_exists = connection.execute(
        """
        SELECT 1
        FROM sqlite_master
        WHERE type = 'table' AND name = 'sqlite_sequence'
        """
    ).fetchone()
    if sequence_exists:
        connection.execute("DELETE FROM sqlite_sequence")

    connection.commit()
    logger.debug("Cleared existing table data")


def insert_categories(
    connection: sqlite3.Connection,
    categories: list[CategoryRecord],
) -> dict[str, int]:
    """Insert categories and return name-to-id mapping."""
    category_ids: dict[str, int] = {}
    for category in categories:
        cursor = connection.execute(
            """
            INSERT INTO categories (name, description)
            VALUES (?, ?)
            """,
            (category.name, category.description),
        )
        category_ids[category.name] = int(cursor.lastrowid)
    return category_ids


def insert_products(
    connection: sqlite3.Connection,
    products: list[ProductRecord],
    category_ids: dict[str, int],
) -> dict[str, int]:
    """Insert products and return SKU-to-id mapping."""
    product_ids: dict[str, int] = {}
    for product in products:
        category_id = category_ids[product.category_name]
        cursor = connection.execute(
            """
            INSERT INTO products (
                category_id,
                sku,
                name,
                description,
                brand,
                unit_price,
                cost_price,
                stock_quantity,
                is_active,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                category_id,
                product.sku,
                product.name,
                product.description,
                product.brand,
                product.unit_price,
                product.cost_price,
                product.stock_quantity,
                product.is_active,
                product.created_at,
                product.updated_at,
            ),
        )
        product_ids[product.sku] = int(cursor.lastrowid)
    return product_ids


def insert_customers(
    connection: sqlite3.Connection,
    customers: list[CustomerRecord],
) -> dict[str, int]:
    """Insert customers and return email-to-id mapping."""
    customer_ids: dict[str, int] = {}
    for customer in customers:
        cursor = connection.execute(
            """
            INSERT INTO customers (
                email,
                first_name,
                last_name,
                city,
                state,
                country,
                signup_date,
                is_active
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                customer.email,
                customer.first_name,
                customer.last_name,
                customer.city,
                customer.state,
                customer.country,
                customer.signup_date,
                customer.is_active,
            ),
        )
        customer_ids[customer.email] = int(cursor.lastrowid)
    return customer_ids


def insert_orders(
    connection: sqlite3.Connection,
    orders: list[OrderRecord],
    customer_ids: dict[str, int],
    product_ids: dict[str, int],
) -> None:
    """Insert orders and related order items."""
    for order in orders:
        customer_id = customer_ids[order.customer_email]
        cursor = connection.execute(
            """
            INSERT INTO orders (
                customer_id,
                order_number,
                order_date,
                status,
                shipping_amount,
                tax_amount,
                discount_amount,
                total_amount,
                payment_method,
                shipping_city,
                shipping_state,
                shipping_country
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                customer_id,
                order.order_number,
                order.order_date,
                order.status,
                order.shipping_amount,
                order.tax_amount,
                order.discount_amount,
                order.total_amount,
                order.payment_method,
                order.shipping_city,
                order.shipping_state,
                order.shipping_country,
            ),
        )
        order_id = int(cursor.lastrowid)

        for item in order.items:
            product_id = product_ids[item.product_sku]
            connection.execute(
                """
                INSERT INTO order_items (
                    order_id,
                    product_id,
                    quantity,
                    unit_price,
                    line_total
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    order_id,
                    product_id,
                    item.quantity,
                    item.unit_price,
                    item.line_total,
                ),
            )


def insert_product_engagement(
    connection: sqlite3.Connection,
    engagement_rows: list[ProductEngagementRecord],
    product_ids: dict[str, int],
) -> None:
    """Insert daily product engagement metrics."""
    for row in engagement_rows:
        product_id = product_ids[row.product_sku]
        connection.execute(
            """
            INSERT INTO product_engagement (
                product_id,
                engagement_date,
                click_count,
                view_sessions,
                time_spent_seconds
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                product_id,
                row.engagement_date,
                row.click_count,
                row.view_sessions,
                row.time_spent_seconds,
            ),
        )


def populate_database(
    connection: sqlite3.Connection,
    *,
    seed: int,
    products_per_category: int,
    customer_count: int,
    order_count: int,
    history_years: int,
    as_of_date: date | None = None,
) -> dict[str, object]:
    """Generate dummy data and write it into the open database connection."""
    rng = build_rng(seed)
    categories = generate_categories()
    products = generate_products(
        rng,
        products_per_category=products_per_category,
        as_of_date=as_of_date,
    )
    customers = generate_customers(
        rng,
        customer_count=customer_count,
        as_of_date=as_of_date,
    )
    orders = generate_orders(
        rng,
        customers=customers,
        products=products,
        order_count=order_count,
        history_years=history_years,
        as_of_date=as_of_date,
    )
    engagement = generate_product_engagement(
        rng,
        products=products,
        orders=orders,
        history_years=history_years,
        as_of_date=as_of_date,
    )

    clear_tables(connection)
    category_ids = insert_categories(connection, categories)
    product_ids = insert_products(connection, products, category_ids)
    customer_ids = insert_customers(connection, customers)
    insert_orders(connection, orders, customer_ids, product_ids)
    insert_product_engagement(connection, engagement, product_ids)
    connection.commit()

    summary = summarize_seed(
        categories=categories,
        products=products,
        customers=customers,
        orders=orders,
        engagement=engagement,
    )
    summary["seed"] = seed
    summary["db_tables"] = {
        "categories": _count_rows(connection, "categories"),
        "products": _count_rows(connection, "products"),
        "customers": _count_rows(connection, "customers"),
        "orders": _count_rows(connection, "orders"),
        "order_items": _count_rows(connection, "order_items"),
        "product_engagement": _count_rows(connection, "product_engagement"),
    }
    summary["monthly_buckets_sample"] = list(monthly_order_buckets(orders))[:3]
    return summary


def _count_rows(connection: sqlite3.Connection, table_name: str) -> int:
    """Return the number of rows in a table."""
    cursor = connection.execute(f"SELECT COUNT(*) AS count FROM {table_name}")
    row = cursor.fetchone()
    return int(row["count"])


def verify_database(connection: sqlite3.Connection) -> dict[str, object]:
    """Run lightweight integrity and analytics checks against the loaded data."""
    checks: dict[str, object] = {}

    integrity = connection.execute("PRAGMA foreign_key_check").fetchall()
    checks["foreign_key_violations"] = len(integrity)

    category_count = _count_rows(connection, "categories")
    checks["category_count"] = category_count
    if category_count > 5:
        raise RuntimeError(f"Expected at most 5 categories, found {category_count}")

    min_products = connection.execute(
        """
        SELECT MIN(product_count) AS min_count
        FROM (
            SELECT category_id, COUNT(*) AS product_count
            FROM products
            GROUP BY category_id
        )
        """
    ).fetchone()["min_count"]
    checks["min_products_per_category"] = int(min_products or 0)
    if int(min_products or 0) < 20:
        raise RuntimeError("Each category must contain at least 20 products")

    date_span = connection.execute(
        """
        SELECT
            MIN(date(order_date)) AS min_date,
            MAX(date(order_date)) AS max_date,
            CAST(
                julianday(MAX(order_date)) - julianday(MIN(order_date)) AS INTEGER
            ) AS span_days
        FROM orders
        """
    ).fetchone()
    checks["order_date_min"] = date_span["min_date"]
    checks["order_date_max"] = date_span["max_date"]
    checks["order_span_days"] = int(date_span["span_days"] or 0)
    if int(date_span["span_days"] or 0) < 365:
        raise RuntimeError(
            "Order history must span at least one full year boundary for multi-year analysis"
        )

    year_count = connection.execute(
        """
        SELECT COUNT(DISTINCT strftime('%Y', order_date)) AS year_count
        FROM orders
        """
    ).fetchone()["year_count"]
    checks["order_year_count"] = int(year_count or 0)
    if int(year_count or 0) < 2:
        raise RuntimeError("Order history must cover at least 2 calendar years")

    top_categories = connection.execute(
        """
        SELECT c.name, ROUND(SUM(oi.line_total), 2) AS revenue
        FROM order_items oi
        JOIN orders o ON o.order_id = oi.order_id
        JOIN products p ON p.product_id = oi.product_id
        JOIN categories c ON c.category_id = p.category_id
        WHERE o.status != 'cancelled'
        GROUP BY c.category_id
        ORDER BY revenue DESC
        """
    ).fetchall()
    checks["revenue_by_category"] = [
        {"category": row["name"], "revenue": row["revenue"]} for row in top_categories
    ]

    status_rows = connection.execute(
        """
        SELECT status, COUNT(*) AS order_count
        FROM orders
        GROUP BY status
        ORDER BY status
        """
    ).fetchall()
    status_counts = {row["status"]: int(row["order_count"]) for row in status_rows}
    checks["order_status_counts"] = status_counts

    expected_statuses = {"ordered", "cancelled", "shipped", "delivered"}
    unexpected = set(status_counts) - expected_statuses
    if unexpected:
        raise RuntimeError(f"Unexpected order statuses found: {sorted(unexpected)}")
    missing = expected_statuses - set(status_counts)
    if missing:
        raise RuntimeError(f"Missing required order statuses in sample data: {sorted(missing)}")

    fulfilled_count = status_counts.get("delivered", 0)
    non_cancelled = sum(
        count for status, count in status_counts.items() if status != "cancelled"
    )
    checks["fulfilled_orders"] = fulfilled_count
    checks["fulfillment_rate"] = (
        round(fulfilled_count / non_cancelled, 4) if non_cancelled else 0.0
    )

    engagement_count = _count_rows(connection, "product_engagement")
    checks["product_engagement_rows"] = engagement_count
    if engagement_count < 1:
        raise RuntimeError("product_engagement must contain daily click and time-spent rows")

    engagement_stats = connection.execute(
        """
        SELECT
            SUM(click_count) AS total_clicks,
            SUM(time_spent_seconds) AS total_time_spent_seconds,
            COUNT(DISTINCT product_id) AS products_with_engagement
        FROM product_engagement
        """
    ).fetchone()
    checks["total_clicks"] = int(engagement_stats["total_clicks"] or 0)
    checks["total_time_spent_hours"] = round(
        int(engagement_stats["total_time_spent_seconds"] or 0) / 3600.0,
        2,
    )
    checks["products_with_engagement"] = int(
        engagement_stats["products_with_engagement"] or 0
    )
    if int(engagement_stats["total_clicks"] or 0) < 1:
        raise RuntimeError("Expected non-zero product clicks for conversion analysis")

    demand_days_without_engagement = connection.execute(
        """
        SELECT COUNT(*) AS missing_count
        FROM (
            SELECT oi.product_id AS product_id, date(o.order_date) AS order_day
            FROM order_items oi
            JOIN orders o ON o.order_id = oi.order_id
            WHERE o.status IN ('ordered', 'shipped', 'delivered')
            GROUP BY oi.product_id, date(o.order_date)
        ) demand
        LEFT JOIN product_engagement pe
            ON pe.product_id = demand.product_id
           AND pe.engagement_date = demand.order_day
        WHERE pe.engagement_id IS NULL
        """
    ).fetchone()["missing_count"]
    checks["demand_days_without_engagement"] = int(demand_days_without_engagement or 0)
    if int(demand_days_without_engagement or 0) > 0:
        raise RuntimeError(
            "Every product/day with non-cancelled demand must have engagement metrics"
        )

    return checks


def prepare_database_file(db_path: Path, overwrite: bool) -> None:
    """Create or replace the target database file as requested."""
    if db_path.exists() and overwrite:
        db_path.unlink()
        logger.info("Removed existing database at %s", db_path)
    elif db_path.exists() and not overwrite:
        logger.info("Reusing existing database file at %s", db_path)


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    parser = create_parser()
    args = parser.parse_args(argv)
    configure_logging(verbose=args.verbose)

    try:
        validate_args(args)
        prepare_database_file(args.db_path, overwrite=args.overwrite)

        with connect_database(args.db_path) as connection:
            apply_schema(connection)
            summary = populate_database(
                connection,
                seed=args.seed,
                products_per_category=args.products_per_category,
                customer_count=args.customers,
                order_count=args.orders,
                history_years=args.history_years,
                as_of_date=args.as_of_date,
            )
            checks = verify_database(connection)

        logger.info("Database ready: %s", args.db_path.resolve())
        logger.info(
            "Loaded %s categories, %s products, %s customers, %s orders, "
            "%s order items, %s engagement rows",
            summary["db_tables"]["categories"],  # type: ignore[index]
            summary["db_tables"]["products"],  # type: ignore[index]
            summary["db_tables"]["customers"],  # type: ignore[index]
            summary["db_tables"]["orders"],  # type: ignore[index]
            summary["db_tables"]["order_items"],  # type: ignore[index]
            summary["db_tables"]["product_engagement"],  # type: ignore[index]
        )
        logger.info(
            "Order history: %s to %s (%s days, %s years represented)",
            checks["order_date_min"],
            checks["order_date_max"],
            checks["order_span_days"],
            checks["order_year_count"],
        )
        logger.info(
            "Order statuses: %s | fulfilled(delivered)=%s rate=%s",
            checks["order_status_counts"],
            checks["fulfilled_orders"],
            checks["fulfillment_rate"],
        )
        logger.info(
            "Engagement: %s rows, %s clicks, %s hours spent across %s products",
            checks["product_engagement_rows"],
            checks["total_clicks"],
            checks["total_time_spent_hours"],
            checks["products_with_engagement"],
        )
        logger.info("Revenue by category: %s", checks["revenue_by_category"])
        return EXIT_SUCCESS
    except (ValueError, FileNotFoundError) as exc:
        logger.error("%s", exc)
        return EXIT_ERROR
    except Exception as exc:  # noqa: BLE001 - top-level CLI guard
        logger.exception("Failed to populate database: %s", exc)
        return EXIT_FAILURE


if __name__ == "__main__":
    sys.exit(main())

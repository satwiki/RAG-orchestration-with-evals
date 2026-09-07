---
title: Local E-commerce SQLite Sample
description: Scripts to create and populate a local SQLite e-commerce database with products, multi-year orders, fulfillment statuses, and product engagement metrics.
ms.date: 2026-09-06
---

# Local E-commerce SQLite Sample

Scripts in this folder create and populate a local SQLite database with
e-commerce style dummy data for analytics and RAG evaluation experiments.

## Tables

| Table | Purpose |
| --- | --- |
| `categories` | Up to 5 product categories |
| `products` | Catalog items (at least 20 per category) |
| `customers` | Customer directory |
| `orders` | Order headers spanning 2+ years with fulfillment status |
| `order_items` | Line items for each order |
| `product_engagement` | Daily clicks, view sessions, and time spent per product |

## Order statuses

Orders use exactly four fulfillment statuses:

| Status | Meaning |
| --- | --- |
| `ordered` | Placed and awaiting fulfillment progress |
| `cancelled` | Not fulfilled |
| `shipped` | In transit |
| `delivered` | Actually fulfilled end state |

Sample data is weighted so most orders reach `delivered`, with smaller shares
for `shipped`, `ordered`, and `cancelled`.

## Product engagement

`product_engagement` stores one row per product per active day:

- `click_count`: product page or listing clicks
- `view_sessions`: sessions that viewed the product
- `time_spent_seconds`: total dwell time that day

Engagement is generated to correlate with non-cancelled order demand on the
same product and date, so conversion-rate analysis is straightforward.

## Default volume

- 5 categories
- 20 products per category (100 products total)
- 120 customers
- 1800 orders across at least 2 years
- Multiple line items per order
- Daily engagement rows correlated with order demand

## Usage

From the repository root, with your virtual environment activated:

```powershell
python src/local_db/ecommerce/populate_db.py --overwrite
```

Use `--overwrite` after schema changes so the database file is recreated.

Custom output path and volumes:

```powershell
python src/local_db/ecommerce/populate_db.py `
  --db-path src/local_db/ecommerce/ecommerce.db `
  --products-per-category 25 `
  --customers 200 `
  --orders 3000 `
  --history-years 3 `
  --seed 42 `
  --overwrite
```

## Useful analytics queries

Monthly revenue (exclude cancelled):

```sql
SELECT strftime('%Y-%m', order_date) AS month,
       COUNT(*) AS order_count,
       ROUND(SUM(total_amount), 2) AS revenue
FROM orders
WHERE status != 'cancelled'
GROUP BY month
ORDER BY month;
```

Fulfillment mix:

```sql
SELECT status,
       COUNT(*) AS order_count,
       ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM orders), 2) AS pct
FROM orders
GROUP BY status
ORDER BY order_count DESC;
```

Actually fulfilled orders (`delivered`) over time:

```sql
SELECT strftime('%Y-%m', order_date) AS month,
       SUM(CASE WHEN status = 'delivered' THEN 1 ELSE 0 END) AS delivered_orders,
       SUM(CASE WHEN status != 'cancelled' THEN 1 ELSE 0 END) AS non_cancelled_orders,
       ROUND(
           1.0 * SUM(CASE WHEN status = 'delivered' THEN 1 ELSE 0 END)
           / NULLIF(SUM(CASE WHEN status != 'cancelled' THEN 1 ELSE 0 END), 0),
           4
       ) AS fulfillment_rate
FROM orders
GROUP BY month
ORDER BY month;
```

Top products by units sold:

```sql
SELECT p.sku, p.name, SUM(oi.quantity) AS units_sold,
       ROUND(SUM(oi.line_total), 2) AS revenue
FROM order_items oi
JOIN products p ON p.product_id = oi.product_id
JOIN orders o ON o.order_id = oi.order_id
WHERE o.status != 'cancelled'
GROUP BY p.product_id
ORDER BY units_sold DESC
LIMIT 20;
```

Category performance by year:

```sql
SELECT strftime('%Y', o.order_date) AS year,
       c.name AS category,
       ROUND(SUM(oi.line_total), 2) AS revenue
FROM order_items oi
JOIN orders o ON o.order_id = oi.order_id
JOIN products p ON p.product_id = oi.product_id
JOIN categories c ON c.category_id = p.category_id
WHERE o.status != 'cancelled'
GROUP BY year, c.category_id
ORDER BY year, revenue DESC;
```

Product conversion proxy (orders and units vs clicks and dwell time):

```sql
SELECT
    p.sku,
    p.name,
    SUM(pe.click_count) AS clicks,
    ROUND(SUM(pe.time_spent_seconds) / 3600.0, 2) AS hours_spent,
    COALESCE(SUM(demand.units_sold), 0) AS units_sold,
    COALESCE(SUM(demand.order_lines), 0) AS order_lines,
    ROUND(
        1.0 * COALESCE(SUM(demand.units_sold), 0) / NULLIF(SUM(pe.click_count), 0),
        4
    ) AS units_per_click
FROM products p
JOIN product_engagement pe ON pe.product_id = p.product_id
LEFT JOIN (
    SELECT
        oi.product_id AS product_id,
        date(o.order_date) AS order_day,
        SUM(oi.quantity) AS units_sold,
        COUNT(*) AS order_lines
    FROM order_items oi
    JOIN orders o ON o.order_id = oi.order_id
    WHERE o.status IN ('ordered', 'shipped', 'delivered')
    GROUP BY oi.product_id, date(o.order_date)
) demand
    ON demand.product_id = pe.product_id
   AND demand.order_day = pe.engagement_date
GROUP BY p.product_id
ORDER BY clicks DESC
LIMIT 20;
```

Daily engagement with order demand side by side:

```sql
SELECT
    pe.engagement_date,
    p.name,
    pe.click_count,
    pe.view_sessions,
    pe.time_spent_seconds,
    ROUND(pe.time_spent_seconds / 3600.0, 2) AS hours_spent,
    COALESCE(SUM(oi.quantity), 0) AS units_ordered
FROM product_engagement pe
JOIN products p ON p.product_id = pe.product_id
LEFT JOIN orders o
    ON date(o.order_date) = pe.engagement_date
   AND o.status IN ('ordered', 'shipped', 'delivered')
LEFT JOIN order_items oi
    ON oi.order_id = o.order_id
   AND oi.product_id = pe.product_id
GROUP BY pe.engagement_id
ORDER BY pe.engagement_date DESC, pe.click_count DESC
LIMIT 50;
```

## Notes

- Data generation is deterministic for a given `--seed`.
- The default database file is `src/local_db/ecommerce/ecommerce.db`.
- Use `--overwrite` to recreate the file from scratch after schema changes.
- `delivered` is the status that means an order was actually fulfilled.
- Engagement metrics are correlated with non-cancelled demand to support
  conversion-rate experiments.

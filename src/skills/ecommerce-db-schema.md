---
name: ecommerce-db-schema
title: E-commerce SQLite Schema Skill
description: Schema for the local e-commerce analytics database used by the LangGraph query workflow.
ms.date: 2026-09-06
---

# E-commerce SQLite Schema Skill

Use this skill when generating SQLite query for the local e-commerce
database at `src/local_db/ecommerce/ecommerce.db`.

## constraints

- Generate **one** SQLite statement only.
- Prefer aggregates and `LIMIT` for analytical answers.
- Order statuses are exactly: `ordered`, `cancelled`, `shipped`, `delivered`.
- `delivered` means actually fulfilled end state.

## Database tables

### categories

| Column | Type | Notes |
| --- | --- | --- |
| category_id | INTEGER PK | |
| name | TEXT UNIQUE | Up to 5 categories |
| description | TEXT | |
| created_at | TEXT | ISO datetime |

### products

| Column | Type | Notes |
| --- | --- | --- |
| product_id | INTEGER PK | |
| category_id | INTEGER FK -> categories | |
| sku | TEXT UNIQUE | |
| name | TEXT | |
| description | TEXT | |
| brand | TEXT | |
| unit_price | REAL | |
| cost_price | REAL | |
| stock_quantity | INTEGER | |
| is_active | INTEGER | 0/1 |
| created_at | TEXT | |
| updated_at | TEXT | |

### customers

| Column | Type | Notes |
| --- | --- | --- |
| customer_id | INTEGER PK | |
| email | TEXT UNIQUE | |
| first_name | TEXT | |
| last_name | TEXT | |
| city | TEXT | |
| state | TEXT | |
| country | TEXT | default US |
| signup_date | TEXT | |
| is_active | INTEGER | 0/1 |

### orders

| Column | Type | Notes |
| --- | --- | --- |
| order_id | INTEGER PK | |
| customer_id | INTEGER FK -> customers | |
| order_number | TEXT UNIQUE | |
| order_date | TEXT | multi-year history |
| status | TEXT | ordered/cancelled/shipped/delivered |
| shipping_amount | REAL | |
| tax_amount | REAL | |
| discount_amount | REAL | |
| total_amount | REAL | |
| payment_method | TEXT | credit_card/debit_card/paypal/apple_pay/gift_card |
| shipping_city | TEXT | |
| shipping_state | TEXT | |
| shipping_country | TEXT | |

### order_items

| Column | Type | Notes |
| --- | --- | --- |
| order_item_id | INTEGER PK | |
| order_id | INTEGER FK -> orders | |
| product_id | INTEGER FK -> products | |
| quantity | INTEGER | |
| unit_price | REAL | |
| line_total | REAL | |

### product_engagement

Daily product engagement for conversion analysis. Correlated with order demand.

| Column | Type | Notes |
| --- | --- | --- |
| engagement_id | INTEGER PK | |
| product_id | INTEGER FK -> products | |
| engagement_date | TEXT | YYYY-MM-DD |
| click_count | INTEGER | clicks that day |
| view_sessions | INTEGER | view sessions that day |
| time_spent_seconds | INTEGER | dwell time that day |

## Useful join patterns

- Product -> category: `products.category_id = categories.category_id`
- Order -> customer: `orders.customer_id = customers.customer_id`
- Line item -> order/product:
  `order_items.order_id = orders.order_id` and
  `order_items.product_id = products.product_id`
- Engagement -> product: `product_engagement.product_id = products.product_id`
- Engagement day to order day: `date(orders.order_date) = product_engagement.engagement_date`

## Output contract for the query generator

Return only SQL text. No markdown fences. No commentary.

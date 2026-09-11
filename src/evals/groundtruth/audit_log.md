---
title: Groundtruth Audit Log
description: Audit history for creation, modification, and removal of RAG groundtruth datasets.
ms.date: 2026-09-10
---

## 2026-09-10

### Updated ecommerce sales analytics

* Dataset: `rag-ecommerce-sales-analytics-20260909.json`
* Operation: Updated
* Samples affected: 8 (`q1` through `q8`)
* Change: Migrated every sample to the latest groundtruth format by replacing
	`input` with `question` and adding `database_id`, `schema_context`,
	`gold_sql`, and `gold_result`
* Verification: Executed all eight gold SQL statements against a temporary
	in-memory SQLite database generated with the frozen date `2026-09-09` and
	seed `42`; every result matched its `gold_result` exactly
* Sources: `src/local_db/ecommerce/schema.sql` and
	`src/local_db/ecommerce/seed_data.py`

## 2026-09-09

### Created ecommerce sales analytics

* Dataset: `rag-ecommerce-sales-analytics-20260909.json`
* Operation: Created
* Samples affected: 8 (`q1` through `q8`)
* Coverage: Product rankings, quarterly revenue trends, fulfillment comparison,
	category performance, geographic sales, payment cancellation rates, top
	customers, and an unsupported-answer edge case for cancellation reasons
* Business use case: E-commerce sales analytics for business analysts and sales
	managers
* Sources: `src/local_db/ecommerce/schema.sql` and
	`src/local_db/ecommerce/seed_data.py` using seed `42`

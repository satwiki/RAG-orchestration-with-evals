---
title: DeepEval Text2SQL harness
description: Design notes for evaluating LangGraph ecommerce analytics output with DeepEval
author: RAG-with-evals maintainers
ms.date: 2026-09-10
ms.topic: concept
---

## Pipeline

Load groundtruth JSON -> map samples to DeepEval `LLMTestCase` records -> invoke
the LangGraph agent -> score SQL execution deterministically -> score the final
answer with GEval.

The evaluator is framework-neutral at the record boundary. LangGraph is the
only implemented adapter today because `src/agentic-maf` has no `agent.py`.

## Dataset mapping

The repository golden file is not a DeepEval JSON list. `dataset.py` maps:

| Groundtruth field | DeepEval field |
|-------------------|----------------|
| `question` | `input` |
| `expected_output` | `expected_output` |
| `claims` | `context` |
| `schema_context` | `retrieval_context` |
| `id`, `gold_sql`, `gold_result`, `database_id` | `additional_metadata` |

`add_goldens_from_json_file` is not used because it expects a top-level JSON
array keyed as `input`.

## Metrics

SQL Execution Accuracy is the release gate. It re-executes gold SQL against the
same database the agent used, then compares normalized result sets. Stored
`gold_result` is a fallback only when live gold SQL fails. Row order is required
only when gold SQL contains `ORDER BY`. Numeric values use a 0.01 absolute
tolerance. Column names are compared case-insensitively.

Answer Correctness is a secondary GEval metric. It can be skipped with
`--skip-llm`.

When gold SQL is rejected by the read-only sandbox, execution accuracy is
treated as skipped-pass so unsupported-answer cases can still be judged on the
natural-language response.

## Multi-turn SQL

LangGraph may emit several queries. The harness scores the last SQL statement
that executed without error.

## Known dataset gaps

The current golden file covers eight sales-analytics questions. It does not
cover product engagement, profit, brand, simple lookups, empty windows, blocked
write intents, or Microsoft Agent Framework.

Gold results were originally verified with seed 42 and frozen date 2026-09-09.
`seed_data.py` uses `date.today()`, so a rebuilt database on another calendar
day will not match stored `gold_result` bytes. Live gold SQL execution keeps
execution scoring valid against the current database.

## Decision log

| Date       | Decision                                                                 | Rationale |
|------------|--------------------------------------------------------------------------|-----------|
| 2026-09-10 | Use DeepEval with a custom execution metric instead of Ragas             | DeepEval is already in requirements.txt; Ragas does not install on this environment |
| 2026-09-10 | Map repository JSON manually instead of `add_goldens_from_json_file`     | DeepEval expects a JSON array of `input` objects |
| 2026-09-10 | Re-execute gold SQL instead of comparing only stored `gold_result`       | Seed generation is anchored to `date.today()` |
| 2026-09-10 | Score the last successful generated SQL                                  | The report builder may run follow-up queries |
| 2026-09-10 | Disable DeepEval `CacheConfig.write_cache` for the CLI harness           | `evaluate()` resets the in-memory test run, then disk reload can call `.load()` on `None` |

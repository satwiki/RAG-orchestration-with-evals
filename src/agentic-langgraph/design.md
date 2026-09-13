---
title: LangGraph e-commerce analytics agent
description: Design notes for the LangGraph text-to-SQL analytics workflow and Streamlit invocation.
ms.date: 2026-09-13
---

# LangGraph e-commerce analytics agent

## Pipeline

`intent_detector` -> `query_generator` -> `query_validator` -> `executor`
-> `report_builder`.

`query_validator` may loop back to `query_generator` on syntax errors
(capped at `MAX_VALIDATION_RETRIES`). `report_builder` may loop back for
deeper analysis (capped at `MAX_TURNS`).

## Skills

`src/skills/ecommerce-db-schema.md` grounds SQL generation. The skill is
framework-agnostic; the LangGraph query generator loads it at runtime.

## Temporal context

The query generator and report builder invoke the `get_current_datetime`
tool at runtime. Explicit dates in a user question take precedence over the
tool result. Relative periods use the tool timestamp as their reference and
are translated into explicit SQL date bounds.

Evaluation runs set `is_evaluation` in `AgentState` and temporarily provide
`RAG_EVAL_AS_OF_DATE` outside the graph. The clock reads that date only when
evaluation mode is explicit. Inference ignores the variable and always uses
the real local date and time. The evaluation date is not carried in
`AgentState`.

## UI invocation

`src/main.py` discovers this folder because it contains `agent.py` and
calls `get_compiled_agent().invoke(...)` (falling back to `ask()`). The
UI lives outside this package so additional frameworks can register the
same way.

## Decision log

| Date | Decision | Rationale |
| --- | --- | --- |
| 2026-09-13 | Gate the frozen evaluation clock behind an explicit state flag | A stale evaluation environment variable cannot affect actual inference, while evaluations remain repeatable without carrying their date in graph state |
| 2026-09-13 | Resolve dates with a runtime clock tool instead of graph state | User-supplied dates remain authoritative while relative periods use the current date; evaluation can still freeze time outside agent state |
| 2026-09-08 | Keep the Streamlit app in `src/main.py` rather than inside this package | The UI must invoke any framework folder under `src/` that exposes `agent.py` |
| 2026-09-08 | Use ChatOpenAI for Foundry v1 endpoints and AzureChatOpenAI for classic resource URLs | AzureChatOpenAI appends `/openai/deployments/...` onto `.../openai/v1` and returns HTTP 404 |

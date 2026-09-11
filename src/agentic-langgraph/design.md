---
title: LangGraph e-commerce analytics agent
description: Design notes for the LangGraph text-to-SQL analytics workflow and Streamlit invocation.
ms.date: 2026-09-08
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

## UI invocation

`src/main.py` discovers this folder because it contains `agent.py` and
calls `get_compiled_agent().invoke(...)` (falling back to `ask()`). The
UI lives outside this package so additional frameworks can register the
same way.

## Decision log

| Date | Decision | Rationale |
| --- | --- | --- |
| 2026-09-08 | Keep the Streamlit app in `src/main.py` rather than inside this package | The UI must invoke any framework folder under `src/` that exposes `agent.py` |
| 2026-09-08 | Use ChatOpenAI for Foundry v1 endpoints and AzureChatOpenAI for classic resource URLs | AzureChatOpenAI appends `/openai/deployments/...` onto `.../openai/v1` and returns HTTP 404 |

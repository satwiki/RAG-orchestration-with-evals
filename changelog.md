---
title: Changelog
description: Semantic version history for RAG-with-evals-samples features.
ms.date: 2026-09-13
---

# Changelog

## 0.3.3 - 2026-09-13

* Reduced duplicate code in evals, and created new utils to promote reusability of common functionalities across the repo.


## 0.3.2 - 2026-09-13

### Fixed

* The LangGraph clock now uses a frozen date only when evaluation mode is
  explicit. Normal inference always uses the real local date and time, even
  if an evaluation date remains in the process environment.

## 0.3.1 - 2026-09-13

### Changed

* LangGraph temporal handling now uses a runtime clock tool. Explicit dates in
  user questions take precedence, while relative periods use the tool result
  without storing an as-of date in graph state.

## 0.3.0 - 2026-09-11

### Added

* Streamlit now visualizes groundtruth datasets, supports validated sample and
  metadata edits, allows adding samples and creating new datasets without a
  delete operation, and runs DeepEval directly from the UI.
* The DeepEval runner exposes structured results for programmatic callers while
  preserving the existing CLI entry point.

## 0.2.1 - 2026-09-11

### Fixed

* DeepEval now creates a deterministic frozen-date SQLite fixture by default,
  configures UTF-8 output on Windows, and records generated SQL history.
* LangGraph relative-date handling uses explicit completed-quarter and
  last-year boundaries, while task-specific schema requirements and complete
  query results are preserved through reporting.

## 0.2.0 - 2026-09-10

### Added

* DeepEval Text2SQL harness in `src/evals/` that loads the ecommerce
  groundtruth JSON, invokes the LangGraph agent, and scores SQL execution
  accuracy plus optional answer correctness.

### Fixed

* DeepEval CLI now sets `CacheConfig(write_cache=False)` so evaluation does
  not crash on `TestRunManager.update_test_run` when the disk test-run
  file is empty or the in-memory run is `None`.

## 0.1.1 - 2026-09-08

### Fixed

* LangGraph LLM client now uses the Foundry v1 chat path when
  `AZURE_AI_FOUNDRY_ENDPOINT` ends with `/openai/v1`, avoiding the 404
  caused by AzureChatOpenAI appending `/openai/deployments/...`.

## 0.1.0 - 2026-09-08

### Added

* Streamlit UI in `src/main.py` that discovers framework folders under `src/`
  (including hyphenated names such as `agentic-langgraph`) and invokes each
  folder's `ask()` or compiled graph entry point.

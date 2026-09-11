---
title: Changelog
description: Semantic version history for RAG-with-evals-samples features.
ms.date: 2026-09-10
---

# Changelog

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

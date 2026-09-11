---
title: Text2SQL Evaluation Framework Research
description: Comparison of local, framework-neutral evaluation frameworks for Text2SQL agents using golden datasets
author: RAG-with-evals maintainers
ms.date: 2026-09-10
ms.topic: concept
keywords:
  - text2sql
  - evaluation
  - ragas
  - deepeval
  - promptfoo
  - mlflow
estimated_reading_time: 10
---

## Executive summary

Ragas is the strongest functional fit for evaluating Text2SQL output because it
provides dedicated metrics for SQL semantic equivalence and result-set
comparison. DeepEval is the lowest-change alternative for this repository
because it is already declared in [requirements.txt](requirements.txt) and has
strong pytest and golden-dataset support. Promptfoo is attractive when local
visual comparison and prompt or model benchmarking are priorities. MLflow is
best reserved for teams that also need experiment tracking, tracing, and
production observability.

The recommended implementation is **Ragas plus pytest**, with a shared,
framework-neutral adapter that accepts the output of either LangGraph or
Microsoft Agent Framework (MAF). Execution accuracy should be the primary
release gate. LLM-based semantic equivalence should remain a secondary metric
for diagnostics and cases where execution is unavailable.

> [!IMPORTANT]
> Running an evaluation framework locally does not guarantee fully offline
> evaluation. Deterministic SQL checks can run without cloud services, but
> LLM-based metrics still contact their configured model provider unless they
> use a local model.

## Requirements

The evaluation framework must meet these requirements:

* No mandatory cloud-hosted evaluation service
* Compatibility with outputs from both LangGraph and MAF
* Support for ground-truth or golden datasets
* Meaningful adoption and active open-source usage
* Suitability for Text2SQL correctness, rather than text similarity alone

Framework compatibility in this comparison means that an evaluator can consume
a normalized input and output record. A native tracing integration is useful,
but it is not required for end-to-end Text2SQL evaluation.

## Comparison summary

Adoption figures are point-in-time indicators observed on 2026-09-10 from the
linked GitHub repositories. They should not be treated as permanent values.

| Framework | Local operation | Golden datasets | Text2SQL capability | Framework compatibility | Adoption signal | Assessment |
|-----------|-----------------|-----------------|---------------------|-------------------------|-----------------|------------|
| Ragas | Yes | Native evaluation datasets and references | Native SQL semantic and result comparison metrics | Black-box integration with either framework | 15.7k GitHub stars | Best Text2SQL fit |
| DeepEval | Yes | Native datasets and goldens | Custom execution metric required | Native LangGraph support; black-box support for MAF | 18.2k GitHub stars | Best low-change fit |
| Promptfoo | Yes | YAML, JSON, and CSV test cases | SQL syntax assertions plus custom Python assertions | Python or API provider adapters | 25k GitHub stars | Best comparison UI |
| MLflow | Yes, including self-hosting | Evaluation datasets and custom scorers | Custom execution scorer required | Native integrations list LangGraph and Microsoft Agent Framework | 27.9k GitHub stars and 60M reported monthly downloads | Best evaluation platform |

## Ragas

Ragas provides two SQL-specific approaches. `SQLSemanticEquivalence` asks an
LLM to determine whether generated and reference queries are semantically
equivalent in the context of a database schema. `DataCompyScore` compares the
result data from generated and expected queries and can report row- or
column-oriented precision, recall, or F1. These capabilities are documented in
the [Ragas SQL metrics reference][ragas-sql].

Ragas evaluation datasets contain homogeneous samples. A `SingleTurnSample`
can include the user input, generated response, and reference answer, which
maps cleanly to a Text2SQL golden record. Ragas also supports conversion from
Hugging Face datasets, as described in its
[evaluation dataset documentation][ragas-datasets].

### Pros

* Includes native SQL semantic-equivalence and result-comparison metrics
* Separates the generated response from the reference value in its dataset model
* Evaluates black-box outputs, keeping the evaluator independent of LangGraph and MAF
* Supports LLM-based and deterministic metrics in the same evaluation pipeline
* Supports multiple model providers through direct adapters and LiteLLM, according to the [model customization guide][ragas-models]
* Uses the Apache 2.0 license and has substantial public adoption, with 15.7k stars and 4.1k dependent repositories reported by [GitHub][ragas-github]

### Cons

* `SQLSemanticEquivalence` depends on an LLM judge and produces a binary score, so results can be less deterministic than query execution
* Fully offline semantic evaluation requires configuring a suitable local judge
* `DataCompyScore` expects comparable result data; the application harness must execute SQL safely and serialize or normalize the result sets
* Execution on one small database instance may miss semantic differences that would appear with other valid data distributions
* Legacy SQL metric classes are deprecated in favor of classes under `ragas.metrics.collections`, which creates migration work for older examples

## DeepEval

DeepEval runs evaluations locally, while its Confident AI service is optional
for centralized reports and monitoring. It can save local JSON results and load
goldens from local JSON, JSONL, and CSV files. These behaviors are documented in
the [DeepEval quickstart][deepeval-quickstart] and
[dataset guide][deepeval-datasets].

DeepEval offers pytest integration, thresholds, caching, parallel evaluation,
and custom metrics. Its documented framework integrations include LangGraph.
For MAF, end-to-end evaluation can remain framework-neutral by converting the
agent result into an `LLMTestCase`, without depending on tracing integration.

### Pros

* Runs evaluation and stores results locally without requiring Confident AI
* Provides a mature golden-dataset model and local file import options
* Integrates with pytest and supports pass or fail thresholds for CI
* Supports standalone black-box evaluation for both agent implementations
* Includes a documented LangGraph callback integration
* Supports custom metrics and local judges such as Ollama
* Is already included in this repository's Python dependencies
* Uses the Apache 2.0 license and reports 18.2k GitHub stars and 308 contributors on [GitHub][deepeval-github]

### Cons

* Does not provide a documented, first-class Text2SQL execution-equivalence metric
* Requires a custom metric for safe SQL execution and normalized result comparison
* Most built-in metrics use an LLM judge, which adds cost and variability when deterministic SQL execution is available
* LangGraph has a documented native integration, while MAF would rely on the shared black-box adapter or manual instrumentation
* Shared cloud dashboards and production monitoring depend on the optional Confident AI service

## Promptfoo

Promptfoo is a local-first CLI and library. Its documentation states that evals
run on the user's machine and communicate directly with the configured model.
It supports Python providers for proprietary applications, local models, APIs,
and custom logic. See the [Promptfoo introduction][promptfoo-intro] and
[Python provider guide][promptfoo-python].

Promptfoo includes deterministic `is-sql` and `contains-sql` assertions. It
also supports custom Python assertions, which can implement query execution and
golden result comparison. The full assertion catalog is available in the
[assertions and metrics documentation][promptfoo-assertions].

### Pros

* Runs locally and supports arbitrary local or remote model providers
* Includes built-in SQL syntax and SQL extraction assertions
* Supports custom Python assertions for execution-based correctness
* Loads declarative test cases and expected values from YAML, JSON, or CSV
* Provides a local matrix viewer for side-by-side prompt and model comparison
* Supports caching, concurrency, named metrics, weighted scores, and CI usage
* Uses the MIT license and reports 25k GitHub stars and 354 contributors on [GitHub][promptfoo-github]

### Cons

* Built-in SQL assertions validate syntax or presence, not semantic correctness
* Execution accuracy still requires a custom Python assertion and database sandbox
* The primary implementation is TypeScript and requires Node.js, adding a second runtime to this Python project
* Provider wrappers and declarative configuration add an integration layer around the existing agents
* Database fixtures and transactional isolation are less natural than direct pytest fixtures

## MLflow

MLflow is a broader AI engineering platform that includes evaluation, tracing,
experiment tracking, prompt management, and monitoring. It can run locally,
self-host on premises, or use a managed deployment. Its integration catalog
lists both LangGraph and Microsoft Agent Framework, and its repository reports
more than 60 million monthly downloads. See the
[MLflow project documentation and adoption data][mlflow-github].

MLflow supports built-in and custom scorers, which makes a deterministic SQL
execution scorer feasible. Its value is strongest when Text2SQL evaluation must
share lineage and observability with other model and agent experiments.

### Pros

* Runs locally or as a self-hosted, vendor-neutral platform
* Lists native tracing integrations for LangGraph and Microsoft Agent Framework
* Combines evaluation results with experiment tracking and application traces
* Supports custom scorers for SQL execution and result comparison
* Provides a local server and UI for comparing runs over time
* Uses the Apache 2.0 license and has the strongest adoption signal in this comparison, with 27.9k stars, 68k dependent repositories, and 60M reported monthly downloads on [GitHub][mlflow-github]

### Cons

* Does not provide a dedicated Text2SQL scorer in the reviewed feature set
* Requires implementation and maintenance of the SQL execution scorer
* Has a larger dependency and operational footprint than a focused evaluation library
* Common workflows benefit from a local tracking server, adding setup and persistence concerns
* Introduces platform capabilities that may be unnecessary for a focused regression suite

## Recommended evaluation design

The evaluator should consume one shared record format regardless of the agent
framework. The existing ground-truth format in this repository already contains
most of the required fields:

```json
{
  "id": "q1",
  "database_id": "ecommerce",
  "question": "Which product generated the most revenue?",
  "schema_context": "Relevant tables and columns",
  "gold_sql": "SELECT ...",
  "gold_result": "Expected normalized result",
  "expected_output": "Expected natural-language answer",
  "claims": ["orders and order_items table references"]
}
```

Both LangGraph and MAF should expose an adapter with the same logical output:

```text
question -> generated_sql -> execution_result -> final_answer
```

The evaluation sequence should apply these checks:

1. Parse the generated output and verify that it contains one permitted,
   read-only SQL statement.
2. Execute the generated query against an isolated database fixture with a
   read-only connection, statement timeout, and row limit.
3. Compare the normalized generated result with the golden result.
4. Use Ragas `SQLSemanticEquivalence` when execution is unavailable or when a
   diagnostic explanation is valuable.
5. Compare the final natural-language answer with the expected answer and
   supporting claims.
6. Record latency, token use, execution failures, and invalid-query rate as
   operational metrics.

Result comparison must define these behaviors explicitly:

* Whether row order matters only when the query contains an ordering requirement
* Whether duplicate rows are significant
* How `NULL` values are normalized
* Which numeric tolerance applies to decimal and floating-point results
* Whether aliases and column names must match
* How dates, timestamps, and time zones are normalized

> [!CAUTION]
> Never execute model-generated SQL against a writable production database.
> Use an isolated fixture, reject multiple statements and non-read-only
> operations, enforce timeouts, and limit returned rows.

## Decision

Adopt **Ragas plus pytest** for Text2SQL evaluation. Use Ragas
`DataCompyScore` or an equivalent deterministic comparator for result accuracy,
and use `SQLSemanticEquivalence` as a secondary signal. Keep agent invocation
behind framework-specific adapters so that the dataset, execution sandbox, and
metrics remain shared across LangGraph and MAF.

DeepEval is the preferred fallback when minimizing dependency and test-harness
change outweighs the benefit of native SQL metrics. In that option, retain the
same execution design and implement it as a custom DeepEval metric. Promptfoo
is a good supplementary choice for interactive prompt or model comparison.
Choose MLflow when experiment lineage, tracing, and operational monitoring are
also explicit requirements.

## Sources

* [Ragas SQL metrics][ragas-sql]
* [Ragas evaluation datasets][ragas-datasets]
* [Ragas model customization][ragas-models]
* [Ragas GitHub repository][ragas-github]
* [DeepEval quickstart][deepeval-quickstart]
* [DeepEval datasets][deepeval-datasets]
* [DeepEval metrics][deepeval-metrics]
* [DeepEval GitHub repository][deepeval-github]
* [Promptfoo introduction][promptfoo-intro]
* [Promptfoo assertions and metrics][promptfoo-assertions]
* [Promptfoo Python provider][promptfoo-python]
* [Promptfoo GitHub repository][promptfoo-github]
* [MLflow GitHub repository][mlflow-github]

[ragas-sql]: https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/sql/
[ragas-datasets]: https://docs.ragas.io/en/stable/concepts/components/eval_dataset/
[ragas-models]: https://docs.ragas.io/en/stable/howtos/customizations/customize_models/
[ragas-github]: https://github.com/vibrantlabsai/ragas
[deepeval-quickstart]: https://deepeval.com/docs/getting-started
[deepeval-datasets]: https://deepeval.com/docs/evaluation-datasets
[deepeval-metrics]: https://deepeval.com/docs/metrics-introduction
[deepeval-github]: https://github.com/confident-ai/deepeval
[promptfoo-intro]: https://www.promptfoo.dev/docs/intro/
[promptfoo-assertions]: https://www.promptfoo.dev/docs/configuration/expected-outputs/
[promptfoo-python]: https://www.promptfoo.dev/docs/providers/python/
[promptfoo-github]: https://github.com/promptfoo/promptfoo
[mlflow-github]: https://github.com/mlflow/mlflow
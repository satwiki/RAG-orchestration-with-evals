#!/usr/bin/env python3
"""Run DeepEval Text2SQL evaluation against the ecommerce analytics agent.

Usage, from the repository root with the virtual environment activated:

    python src/evals/run_deepeval.py
    python src/evals/run_deepeval.py --skip-llm
    python src/evals/run_deepeval.py --limit 1 --sample-id q1
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from deepeval import evaluate
from deepeval.evaluate.configs import (
    AsyncConfig,
    CacheConfig,
    DisplayConfig,
    ErrorConfig,
)
from deepeval.test_case import LLMTestCase

EXIT_SUCCESS = 0
EXIT_FAILURE = 1
EXIT_ERROR = 2

EVAL_DIR = Path(__file__).resolve().parent
SRC_DIR = EVAL_DIR.parent
REPO_ROOT = SRC_DIR.parent
DEFAULT_DB_PATH = Path("src/local_db/ecommerce/ecommerce.db")
RESULTS_DIR = EVAL_DIR / "results"

if str(EVAL_DIR) not in sys.path:
    sys.path.insert(0, str(EVAL_DIR))
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from agent_adapter import DEFAULT_FRAMEWORK, invoke_agent
from dataset import (
    GroundtruthSample,
    default_dataset_path,
    load_groundtruth,
    sample_to_golden,
)
from metrics import (
    SqlExecutionAccuracyMetric,
    build_answer_correctness_metric,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class EvaluationMetricResult:
    """One metric result produced for one groundtruth sample."""

    sample_id: str
    metric_name: str
    score: float | None
    success: bool
    reason: str


@dataclass(frozen=True)
class EvaluationRunSummary:
    """Structured result returned by both the CLI and Streamlit UI."""

    exit_code: int
    dataset_path: Path
    framework: str
    sample_count: int
    metric_results: list[EvaluationMetricResult]


def write_evaluation_results(
    summary: EvaluationRunSummary,
    *,
    results_dir: Path = RESULTS_DIR,
    generated_at: datetime | None = None,
) -> Path:
    """Write one timestamped, human-readable evaluation result file."""
    timestamp = generated_at or datetime.now().astimezone()
    output_path = results_dir / f"deepeval-results-{timestamp:%Y%m%dT%H%M%S.%f%z}.txt"
    lines = [
        "DeepEval Evaluation Results",
        f"Generated at: {timestamp.isoformat()}",
        f"Dataset: {summary.dataset_path}",
        f"Framework: {summary.framework}",
        f"Sample count: {summary.sample_count}",
        f"Exit code: {summary.exit_code}",
        "",
        "Metric results",
    ]
    if not summary.metric_results:
        lines.append("No metric results were produced.")
    for index, metric in enumerate(summary.metric_results, start=1):
        reason = metric.reason.replace("\n", "\n  ") or "None"
        lines.extend(
            [
                "",
                f"[{index}] {metric.sample_id}",
                f"Metric: {metric.metric_name}",
                f"Score: {metric.score}",
                f"Success: {metric.success}",
                f"Reason: {reason}",
            ]
        )

    results_dir.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    logger.info("\n ✅ Evaluation results written to %s\n", output_path)
    return output_path


def configure_output_encoding() -> None:
    """Prevent DeepEval's Unicode progress output from failing on Windows."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            reconfigure(encoding="utf-8", errors="replace")


def configure_logging(verbose: bool = False) -> None:
    """Configure root logging for CLI usage."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=level, format="%(levelname)s: %(message)s")


def create_parser() -> argparse.ArgumentParser:
    """Create and configure the evaluation CLI parser."""
    parser = argparse.ArgumentParser(
        description="Evaluate the ecommerce Text2SQL agent with DeepEval."
    )
    parser.add_argument(
        "--dataset",
        type=Path,
        default=default_dataset_path(),
        help="Path to the groundtruth JSON file.",
    )
    parser.add_argument(
        "--framework",
        default=DEFAULT_FRAMEWORK,
        help="Framework folder under src/ that contains agent.py.",
    )
    parser.add_argument(
        "--db-path",
        type=Path,
        default=None,
        help=f"SQLite database used for execution scoring (default: {DEFAULT_DB_PATH}).",
    )
    parser.add_argument(
        "--sample-id",
        action="append",
        dest="sample_ids",
        help="Limit evaluation to one or more sample ids (repeatable).",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Evaluate at most N samples after filtering.",
    )
    parser.add_argument(
        "--skip-llm",
        action="store_true",
        help="Skip the GEval answer-correctness metric and run execution accuracy only.",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable debug logging.",
    )
    return parser


def resolve_db_path(cli_path: Path | None = None) -> Path:
    """Resolve the local SQLite database or an explicitly supplied path."""
    selected_path = cli_path or DEFAULT_DB_PATH
    db_path = (
        selected_path
        if selected_path.is_absolute()
        else (REPO_ROOT / selected_path).resolve()
    )
    os.environ["ECOMMERCE_DB_PATH"] = str(db_path)
    return db_path


def select_samples(
    samples: list[GroundtruthSample],
    sample_ids: list[str] | None,
    limit: int | None,
) -> list[GroundtruthSample]:
    """Filter samples by id and optional limit."""
    selected = samples
    if sample_ids:
        wanted = set(sample_ids)
        selected = [sample for sample in samples if sample.id in wanted]
        missing = wanted - {sample.id for sample in selected}
        if missing:
            raise ValueError(f"Unknown sample ids: {sorted(missing)}")
    if limit is not None:
        if limit < 1:
            raise ValueError("--limit must be at least 1")
        selected = selected[:limit]
    if not selected:
        raise ValueError("No samples selected for evaluation.")
    return selected


def build_test_case(sample: GroundtruthSample, framework: str) -> LLMTestCase:
    """Invoke the agent for one golden sample and build a DeepEval test case."""
    golden = sample_to_golden(sample)
    run = invoke_agent(
        sample.question,
        framework_name=framework,
        task_context=sample.schema_context,
        required_output_columns=list(json.loads(sample.gold_result)[0].keys()),
    )
    metadata = dict(golden.additional_metadata or {})
    metadata["generated_sql"] = run.generated_sql
    metadata["generated_sql_history"] = [
        record.get("sql") for record in run.query_history if record.get("sql")
    ]
    metadata["query_history"] = run.query_history
    metadata["blocked"] = run.blocked
    metadata["intent_reason"] = run.intent_reason
    metadata["query_count"] = len(run.query_history)
    logger.debug("%s generated SQL history: %s", sample.id, metadata["generated_sql_history"])
    return LLMTestCase(
        input=sample.question,
        actual_output=run.final_answer,
        expected_output=sample.expected_output,
        context=list(sample.claims),
        retrieval_context=[sample.schema_context],
        additional_metadata=metadata,
        name=sample.id,
        comments=sample.schema_context,
    )


def run_evaluation(
    *,
    dataset_path: Path | None = None,
    framework: str = DEFAULT_FRAMEWORK,
    db_path: Path | None = None,
    sample_ids: list[str] | None = None,
    limit: int | None = None,
    skip_llm: bool = False,
) -> EvaluationRunSummary:
    """Run DeepEval and return structured results for CLI or UI callers."""
    configure_output_encoding()
    dataset_file = dataset_path or default_dataset_path()
    dataset = load_groundtruth(dataset_file)
    samples = select_samples(dataset.samples, sample_ids, limit)
    resolved_db_path = resolve_db_path(db_path)
    if not resolved_db_path.is_file():
        logger.error("Database not found: %s.", resolved_db_path)
        summary = EvaluationRunSummary(
            exit_code=EXIT_ERROR,
            dataset_path=dataset.path,
            framework=framework,
            sample_count=len(samples),
            metric_results=[],
        )
        write_evaluation_results(summary)
        return summary

    logger.info(
        "Evaluating %s sample(s) with framework=%s db=%s",
        len(samples),
        framework,
        resolved_db_path,
    )

    test_cases = [build_test_case(sample, framework) for sample in samples]
    metrics = [SqlExecutionAccuracyMetric(db_path=resolved_db_path)]
    if not skip_llm:
        metrics.append(build_answer_correctness_metric())

    result = evaluate(
        test_cases=test_cases,
        metrics=metrics,
        identifier="ecommerce-text2sql-deepeval",
        async_config=AsyncConfig(run_async=False),
        display_config=DisplayConfig(show_indicator=True, print_results=True),
        cache_config=CacheConfig(write_cache=False, use_cache=False),
        error_config=ErrorConfig(ignore_errors=False, skip_on_missing_params=False),
    )

    metric_results: list[EvaluationMetricResult] = []
    failures = 0
    for test_result in result.test_results:
        sample_name = test_result.name or test_result.input
        for metric_data in test_result.metrics_data or []:
            passed = bool(metric_data.success)
            metric_results.append(
                EvaluationMetricResult(
                    sample_id=sample_name,
                    metric_name=metric_data.name,
                    score=metric_data.score,
                    success=passed,
                    reason=metric_data.reason or "",
                )
            )
            logger.info(
                "%s | %s | score=%s | success=%s | %s",
                sample_name,
                metric_data.name,
                metric_data.score,
                passed,
                metric_data.reason,
            )
            if metric_data.name == "SQL Execution Accuracy" and not passed:
                failures += 1
    if failures:
        logger.error("Execution accuracy failed for %s sample(s).", failures)
        exit_code = EXIT_FAILURE
    else:
        logger.info("Execution accuracy passed for all evaluated samples.")
        exit_code = EXIT_SUCCESS
    summary = EvaluationRunSummary(
        exit_code=exit_code,
        dataset_path=dataset.path,
        framework=framework,
        sample_count=len(samples),
        metric_results=metric_results,
    )
    write_evaluation_results(summary)
    return summary


def main(argv: list[str] | None = None) -> int:
    """Run DeepEval against selected groundtruth samples."""
    parser = create_parser()
    args = parser.parse_args(argv)
    configure_logging(args.verbose)

    try:
        summary = run_evaluation(
            dataset_path=args.dataset,
            framework=args.framework,
            db_path=args.db_path,
            sample_ids=args.sample_ids,
            limit=args.limit,
            skip_llm=args.skip_llm,
        )
        return summary.exit_code
    except ValueError as exc:
        logger.error("%s", exc)
        return EXIT_ERROR
    except KeyboardInterrupt:
        logger.error("Interrupted.")
        return 130


if __name__ == "__main__":
    sys.exit(main())

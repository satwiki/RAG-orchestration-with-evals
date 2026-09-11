#!/usr/bin/env python3
"""Run DeepEval Text2SQL evaluation against the ecommerce analytics agent.

Usage, from the repository root with the virtual environment activated:

    python src/evals/run_deepeval.py
    python src/evals/run_deepeval.py --skip-llm
    python src/evals/run_deepeval.py --limit 1 --sample-id q1
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

from deepeval import evaluate
from deepeval.evaluate.configs import AsyncConfig, CacheConfig, DisplayConfig, ErrorConfig
from deepeval.test_case import LLMTestCase
from dotenv import load_dotenv

EXIT_SUCCESS = 0
EXIT_FAILURE = 1
EXIT_ERROR = 2

EVAL_DIR = Path(__file__).resolve().parent
SRC_DIR = EVAL_DIR.parent
REPO_ROOT = SRC_DIR.parent

if str(EVAL_DIR) not in sys.path:
    sys.path.insert(0, str(EVAL_DIR))
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from agent_adapter import DEFAULT_FRAMEWORK, invoke_agent  # noqa: E402
from dataset import (  # noqa: E402
    GroundtruthSample,
    default_dataset_path,
    load_groundtruth,
    log_coverage_gaps,
    sample_to_golden,
)
from metrics import SqlExecutionAccuracyMetric, build_answer_correctness_metric  # noqa: E402

logger = logging.getLogger(__name__)


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
        help="SQLite database used for execution scoring (default: ECOMMERCE_DB_PATH or local ecommerce.db).",
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


def resolve_db_path(cli_path: Path | None) -> Path:
    """Load .env and resolve the ecommerce SQLite path."""
    load_dotenv(REPO_ROOT / ".env")
    if cli_path is not None:
        db_path = cli_path if cli_path.is_absolute() else (REPO_ROOT / cli_path).resolve()
    else:
        raw_path = os.environ.get("ECOMMERCE_DB_PATH")
        if raw_path:
            db_path = Path(raw_path)
            if not db_path.is_absolute():
                db_path = (REPO_ROOT / db_path).resolve()
        else:
            db_path = REPO_ROOT / "src" / "local_db" / "ecommerce" / "ecommerce.db"
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
    run = invoke_agent(sample.question, framework_name=framework)
    metadata = dict(golden.additional_metadata or {})
    metadata["generated_sql"] = run.generated_sql
    metadata["blocked"] = run.blocked
    metadata["intent_reason"] = run.intent_reason
    metadata["query_count"] = len(run.query_history)
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


def main(argv: list[str] | None = None) -> int:
    """Run DeepEval against selected groundtruth samples."""
    parser = create_parser()
    args = parser.parse_args(argv)
    configure_logging(args.verbose)

    try:
        db_path = resolve_db_path(args.db_path)
        if not db_path.is_file():
            logger.error("Database not found: %s. Run populate_db.py first.", db_path)
            return EXIT_ERROR

        dataset = load_groundtruth(args.dataset)
        log_coverage_gaps(dataset)
        samples = select_samples(dataset.samples, args.sample_ids, args.limit)
        logger.info("Evaluating %s sample(s) with framework=%s db=%s", len(samples), args.framework, db_path)

        test_cases = [build_test_case(sample, args.framework) for sample in samples]
        metrics = [SqlExecutionAccuracyMetric(db_path=db_path)]
        if not args.skip_llm:
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

        failures = 0
        for test_result in result.test_results:
            sample_name = test_result.name or test_result.input
            for metric_data in test_result.metrics_data or []:
                passed = bool(metric_data.success)
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
            return EXIT_FAILURE
        logger.info("Execution accuracy passed for all evaluated samples.")
        return EXIT_SUCCESS
    except ValueError as exc:
        logger.error("%s", exc)
        return EXIT_ERROR
    except KeyboardInterrupt:
        logger.error("Interrupted.")
        return 130


if __name__ == "__main__":
    sys.exit(main())

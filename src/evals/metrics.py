"""DeepEval metrics for Text2SQL execution accuracy and answer correctness."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

from deepeval.metrics import BaseMetric, GEval
from deepeval.models import AzureOpenAIModel, DeepEvalBaseLLM
from deepeval.test_case import LLMTestCase, LLMTestCaseParams
from openai import AzureOpenAI, OpenAI

from sql_sandbox import (
    QueryRejectedError,
    execute_readonly_query,
    parse_result_payload,
    results_equivalent,
    sql_requires_row_order,
)

logger = logging.getLogger(__name__)


class SqlExecutionAccuracyMetric(BaseMetric):
    """Deterministic metric that compares generated SQL results to gold SQL results."""

    def __init__(self, db_path: Path, threshold: float = 1.0) -> None:
        """Configure the metric against an isolated SQLite database.

        Args:
            db_path: SQLite file used to execute generated and gold SQL.
            threshold: Minimum score required for success. Defaults to 1.0.
        """
        self.db_path = Path(db_path)
        self.threshold = threshold
        self.async_mode = False
        self.include_reason = True
        self.score: float | None = None
        self.reason: str | None = None
        self.success: bool | None = None
        self.error: str | None = None

    def measure(self, test_case: LLMTestCase, *args: Any, **kwargs: Any) -> float:
        """Execute generated SQL and compare the result set to gold SQL."""
        metadata = test_case.additional_metadata or {}
        generated_sql = (metadata.get("generated_sql") or "").strip()
        gold_sql = (metadata.get("gold_sql") or "").strip()
        stored_gold_result = metadata.get("gold_result")

        if not gold_sql:
            self.score = 0.0
            self.reason = "Golden record is missing gold_sql."
            self.success = False
            return self.score

        try:
            expected_rows = execute_readonly_query(gold_sql, self.db_path)
            expected_source = "live gold SQL"
        except QueryRejectedError as exc:
            self.score = 1.0
            self.reason = (
                f"Gold SQL is not sandbox-executable ({exc}). "
                "Execution accuracy is skipped; answer correctness still applies."
            )
            self.success = True
            return self.score
        except Exception as exc:  # noqa: BLE001 - metric must record the failure
            try:
                expected_rows = parse_result_payload(stored_gold_result)
                expected_source = "stored gold_result (live gold SQL failed)"
                logger.warning("Live gold SQL failed (%s); using stored gold_result.", exc)
            except Exception as parse_exc:  # noqa: BLE001
                self.score = 0.0
                self.reason = f"Unable to obtain gold rows: {exc}; {parse_exc}"
                self.success = False
                return self.score

        if not generated_sql:
            self.score = 0.0
            self.reason = "Agent did not produce a successful SQL statement."
            self.success = False
            return self.score

        try:
            actual_rows = execute_readonly_query(generated_sql, self.db_path)
        except QueryRejectedError as exc:
            self.score = 0.0
            self.reason = f"Generated SQL was rejected: {exc}"
            self.success = False
            return self.score
        except Exception as exc:  # noqa: BLE001 - metric must record the failure
            self.score = 0.0
            self.reason = f"Generated SQL failed to execute: {exc}"
            self.success = False
            return self.score

        matched, compare_reason = results_equivalent(
            actual_rows,
            expected_rows,
            order_matters=sql_requires_row_order(gold_sql),
        )
        self.score = 1.0 if matched else 0.0
        self.reason = f"{compare_reason} (expected from {expected_source})."
        self.success = matched
        return self.score

    async def a_measure(self, test_case: LLMTestCase, *args: Any, **kwargs: Any) -> float:
        """Run the synchronous measure path; this metric is deterministic."""
        return self.measure(test_case, *args, **kwargs)

    def is_successful(self) -> bool:
        """Return True when the score meets the threshold and no error was set."""
        if self.error is not None:
            self.success = False
        else:
            self.success = (self.score or 0.0) >= self.threshold
        return bool(self.success)

    @property
    def __name__(self) -> str:
        """Human-readable metric name shown in DeepEval output."""
        return "SQL Execution Accuracy"


def _normalize_azure_endpoint(endpoint: str) -> str:
    """Strip whitespace and a trailing slash from an Azure / Foundry endpoint URL."""
    return endpoint.strip().rstrip("/")


class FoundryChatJudge(DeepEvalBaseLLM):
    """DeepEval judge that uses the same Foundry or Azure OpenAI settings as the agent."""

    def load_model(self) -> OpenAI | AzureOpenAI:
        """Build the chat client used to score natural-language answers."""
        endpoint = _normalize_azure_endpoint(os.environ["AZURE_AI_FOUNDRY_ENDPOINT"])
        api_key = os.environ["AZURE_AI_FOUNDRY_API_KEY"]
        if endpoint.endswith("/openai/v1"):
            return OpenAI(base_url=endpoint, api_key=api_key)
        return AzureOpenAI(
            azure_endpoint=endpoint,
            api_key=api_key,
            api_version=os.environ.get("AZURE_OPENAI_API_VERSION", "2024-12-01-preview"),
        )

    def generate(self, prompt: str) -> str:
        """Return a single judge completion."""
        deployment = os.environ.get("AZURE_AI_FOUNDRY_DEPLOYMENT") or "gpt-5.4-nano"
        response = self.model.chat.completions.create(
            model=deployment,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
        )
        return response.choices[0].message.content or ""

    async def a_generate(self, prompt: str) -> str:
        """Return a single async judge completion."""
        return self.generate(prompt)

    def get_model_name(self) -> str:
        """Return the configured deployment name."""
        return os.environ.get("AZURE_AI_FOUNDRY_DEPLOYMENT") or "gpt-5.4-nano"


def build_judge_model() -> DeepEvalBaseLLM:
    """Create a DeepEval judge from environment credentials.

    Foundry v1 bases (`.../openai/v1`) cannot use AzureOpenAIModel, which
    appends `/openai/deployments/{name}`. Classic Azure OpenAI endpoints use
    AzureOpenAIModel directly.
    """
    endpoint = _normalize_azure_endpoint(os.environ["AZURE_AI_FOUNDRY_ENDPOINT"])
    deployment = os.environ.get("AZURE_AI_FOUNDRY_DEPLOYMENT") or "gpt-5.4-nano"
    api_key = os.environ["AZURE_AI_FOUNDRY_API_KEY"]
    if endpoint.endswith("/openai/v1"):
        return FoundryChatJudge(model_name=deployment)
    return AzureOpenAIModel(
        model_name=deployment,
        deployment_name=deployment,
        azure_openai_api_key=api_key,
        openai_api_version=os.environ.get("AZURE_OPENAI_API_VERSION", "2024-12-01-preview"),
        azure_endpoint=endpoint,
        temperature=0,
    )


def build_answer_correctness_metric(model: DeepEvalBaseLLM | None = None) -> GEval:
    """Build a GEval metric that scores the final answer against expected_output and claims."""
    return GEval(
        name="Answer Correctness",
        criteria=(
            "Determine whether the actual output answers the input using the same facts as "
            "the expected output. Numeric values, rankings, time windows, and unsupported-"
            "answer statements must match. Wording may differ. Use context as supporting claims."
        ),
        evaluation_params=[
            LLMTestCaseParams.INPUT,
            LLMTestCaseParams.ACTUAL_OUTPUT,
            LLMTestCaseParams.EXPECTED_OUTPUT,
            LLMTestCaseParams.CONTEXT,
        ],
        evaluation_steps=[
            "Identify the key facts, numbers, entities, and time windows in expected_output.",
            "Check that actual_output includes those facts without contradicting them.",
            "If expected_output says the data cannot answer the question, pass only when "
            "actual_output also refuses to invent a causal or unsupported answer.",
            "Ignore markdown formatting and minor wording differences.",
            "Score 1.0 when facts match, 0.0 when a material fact is missing or wrong.",
        ],
        model=model or build_judge_model(),
        threshold=0.7,
        async_mode=False,
        strict_mode=False,
    )

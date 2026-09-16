"""Load framework-neutral groundtruth JSON into DeepEval goldens."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

from deepeval.dataset.golden import Golden

logger = logging.getLogger(__name__)

REQUIRED_SAMPLE_FIELDS = (
    "id",
    "database_id",
    "question",
    "schema_context",
    "gold_sql",
    "gold_result",
    "expected_output",
    "claims",
)


@dataclass(frozen=True)
class GroundtruthSample:
    """One Text2SQL evaluation sample from the repository golden file."""

    id: str
    database_id: str
    question: str
    schema_context: str
    gold_sql: str
    gold_result: str
    expected_output: str
    claims: list[str]


@dataclass(frozen=True)
class GroundtruthDataset:
    """A loaded golden file plus its metadata."""

    path: Path
    metadata: dict[str, Any]
    samples: list[GroundtruthSample]


def default_dataset_path() -> Path:
    """Return the default ecommerce sales analytics golden file."""
    return (
        Path(__file__).resolve().parent
        / "groundtruth"
        / "rag-ecommerce-sales-analytics-20260909.json"
    )


def dataset_as_of_date(dataset: GroundtruthDataset) -> date:
    """Return the frozen analysis date declared by a groundtruth dataset."""
    raw_date = (
        dataset.metadata.get("as_of_date")
        or str(dataset.metadata.get("created_at", ""))[:10]
    )
    try:
        return date.fromisoformat(raw_date)
    except ValueError as exc:
        raise ValueError(
            f"Groundtruth metadata must provide a valid as_of_date, got {raw_date!r}."
        ) from exc


def load_groundtruth(path: Path | None = None) -> GroundtruthDataset:
    """Load and validate the repository groundtruth JSON file.

    Args:
        path: Optional override path. Defaults to the ecommerce sales analytics file.

    Returns:
        Parsed dataset with typed samples.

    Raises:
        FileNotFoundError: If the JSON file is missing.
        ValueError: If required metadata or sample fields are missing.
    """
    dataset_path = path or default_dataset_path()
    payload = json.loads(dataset_path.read_text(encoding="utf-8"))
    return parse_groundtruth_payload(payload, dataset_path)


def parse_groundtruth_payload(payload: Any, dataset_path: Path) -> GroundtruthDataset:
    """Validate and parse an in-memory groundtruth document."""
    if not isinstance(payload, dict):
        raise ValueError(
            f"{dataset_path} must contain a JSON object with metadata and samples."
        )

    metadata = payload.get("metadata")
    samples_payload = payload.get("samples")
    if not isinstance(metadata, dict):
        raise ValueError("Groundtruth file is missing a metadata object.")
    if not isinstance(samples_payload, list) or not samples_payload:
        raise ValueError("Groundtruth file must contain a non-empty samples array.")

    samples: list[GroundtruthSample] = []
    seen_ids: set[str] = set()
    for index, raw in enumerate(samples_payload):
        if not isinstance(raw, dict):
            raise ValueError(f"Sample at index {index} is not an object.")
        missing = [field for field in REQUIRED_SAMPLE_FIELDS if field not in raw]
        if missing:
            raise ValueError(f"Sample at index {index} is missing fields: {missing}")
        sample_id = str(raw["id"])
        if sample_id in seen_ids:
            raise ValueError(f"Duplicate sample id: {sample_id}")
        seen_ids.add(sample_id)
        claims = raw["claims"]
        if not isinstance(claims, list) or not all(
            isinstance(claim, str) for claim in claims
        ):
            raise ValueError(f"Sample {sample_id} claims must be a list of strings.")
        samples.append(
            GroundtruthSample(
                id=sample_id,
                database_id=str(raw["database_id"]),
                question=str(raw["question"]),
                schema_context=str(raw["schema_context"]),
                gold_sql=str(raw["gold_sql"]),
                gold_result=raw["gold_result"]
                if isinstance(raw["gold_result"], str)
                else json.dumps(raw["gold_result"]),
                expected_output=str(raw["expected_output"]),
                claims=list(claims),
            )
        )
    return GroundtruthDataset(path=dataset_path, metadata=metadata, samples=samples)


def save_groundtruth(path: Path, payload: dict[str, Any]) -> GroundtruthDataset:
    """Validate and atomically save a groundtruth document in repository format."""
    dataset = parse_groundtruth_payload(payload, path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_name(f".{path.name}.tmp")
    temporary_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    temporary_path.replace(path)
    return dataset


def sample_to_golden(sample: GroundtruthSample) -> Golden:
    """Map a repository sample onto DeepEval's Golden model.

    DeepEval goldens use `input` rather than `question`. Text2SQL fields that
    DeepEval does not model natively are stored in additional_metadata.
    """
    return Golden(
        input=sample.question,
        expected_output=sample.expected_output,
        context=list(sample.claims),
        retrieval_context=[sample.schema_context],
        additional_metadata={
            "id": sample.id,
            "database_id": sample.database_id,
            "gold_sql": sample.gold_sql,
            "gold_result": sample.gold_result,
            "claims": list(sample.claims),
        },
        name=sample.id,
        comments=sample.schema_context,
    )

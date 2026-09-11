"""Framework-neutral adapter that invokes a Text2SQL agent and normalizes output."""

from __future__ import annotations

import importlib.util
import sys
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Any

from langchain_core.messages import HumanMessage

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = REPO_ROOT / "src"
DEFAULT_FRAMEWORK = "agentic-langgraph"


@dataclass(frozen=True)
class AgentRunResult:
    """Normalized agent output consumed by the evaluator."""

    question: str
    final_answer: str
    blocked: bool
    intent_reason: str | None
    query_history: list[dict[str, Any]]
    generated_sql: str | None


def framework_dir(name: str = DEFAULT_FRAMEWORK) -> Path:
    """Resolve a framework folder under src/."""
    path = SRC_DIR / name
    if not (path / "agent.py").is_file():
        raise FileNotFoundError(f"No agent.py found for framework '{name}' at {path}")
    return path


def _ensure_on_sys_path(path: Path) -> None:
    """Prepend path to sys.path when it is not already present."""
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)


def load_framework_agent_module(framework_path: Path) -> ModuleType:
    """Load agent.py from a framework folder, including hyphenated names."""
    agent_file = framework_path / "agent.py"
    _ensure_on_sys_path(framework_path)
    _ensure_on_sys_path(framework_path.parent)
    resolved = framework_path.resolve()
    module_name = f"eval_agent_{framework_path.name.replace('-', '_')}_{abs(hash(str(resolved)))}"
    existing = sys.modules.get(module_name)
    if existing is not None:
        return existing
    spec = importlib.util.spec_from_file_location(module_name, agent_file)
    if spec is None or spec.loader is None:
        raise ImportError(f"Unable to load agent module from {agent_file}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _last_successful_sql(history: list[dict[str, Any]]) -> str | None:
    """Return the last generated SQL that executed without error."""
    for record in reversed(history):
        sql = (record.get("sql") or "").strip()
        if sql and not record.get("error"):
            return sql
    for record in reversed(history):
        sql = (record.get("sql") or "").strip()
        if sql:
            return sql
    return None


def invoke_agent(question: str, framework_name: str = DEFAULT_FRAMEWORK) -> AgentRunResult:
    """Run a framework agent and return SQL history plus the final answer.

    Prefers get_compiled_agent().invoke so query_history is available. Falls
    back to ask(question), which cannot supply SQL for execution scoring.
    """
    stripped = question.strip()
    if not stripped:
        raise ValueError("Question must not be empty.")

    module = load_framework_agent_module(framework_dir(framework_name))
    get_compiled = getattr(module, "get_compiled_agent", None)
    if callable(get_compiled):
        result = get_compiled().invoke(
            {"user_question": stripped, "messages": [HumanMessage(content=stripped)]}
        )
        history = list(result.get("query_history") or [])
        return AgentRunResult(
            question=stripped,
            final_answer=result.get("final_answer") or "",
            blocked=bool(result.get("blocked")),
            intent_reason=result.get("intent_reason"),
            query_history=history,
            generated_sql=_last_successful_sql(history),
        )

    ask_fn = getattr(module, "ask", None)
    if callable(ask_fn):
        return AgentRunResult(
            question=stripped,
            final_answer=ask_fn(stripped) or "",
            blocked=False,
            intent_reason=None,
            query_history=[],
            generated_sql=None,
        )

    raise AttributeError(f"{framework_name} agent.py must expose ask() or get_compiled_agent().")

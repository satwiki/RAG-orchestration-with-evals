#!/usr/bin/env python3
"""Streamlit UI that invokes framework-specific agents under ``src/``.

Discover folders that contain ``agent.py`` (for example ``agentic-langgraph``)
and call each package's ``ask()`` / compiled graph entry point.

Usage:
    streamlit run src/main.py
"""

from __future__ import annotations

import importlib.util
import logging
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Any

import streamlit as st
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage

EXIT_SUCCESS = 0
EXIT_FAILURE = 1

SRC_DIR = Path(__file__).resolve().parent
REPO_ROOT = SRC_DIR.parent

_SKIP_DIR_NAMES = frozenset(
    {
        "notebooks",
        "local_db",
        "prompts",
        "skills",
        "faiss_store",
        "utils",
        "__pycache__",
    }
)
_FRAMEWORK_LABELS = {
    "agentic-langgraph": "LangGraph",
    "langgraph": "LangGraph",
    "maf": "Microsoft Agent Framework",
}

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class FrameworkSpec:
    """A framework folder under ``src/`` that exposes an agent entry point."""

    name: str
    path: Path
    display_name: str


def configure_logging(verbose: bool = False) -> None:
    """Configure logging based on verbosity level."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=level, format="%(levelname)s: %(message)s")


def configure_environment(repo_root: Path = REPO_ROOT) -> Path:
    """Load ``.env`` and resolve ``ECOMMERCE_DB_PATH`` against the repo root.

    Args:
        repo_root: Repository root that contains ``.env`` and ``src/``.

    Returns:
        Absolute path to the e-commerce SQLite database.
    """
    load_dotenv(repo_root / ".env")
    raw_path = os.environ.get("ECOMMERCE_DB_PATH")
    if raw_path:
        db_path = Path(raw_path)
        if not db_path.is_absolute():
            db_path = (repo_root / db_path).resolve()
    else:
        db_path = repo_root / "src" / "local_db" / "ecommerce" / "ecommerce.db"
    os.environ["ECOMMERCE_DB_PATH"] = str(db_path)
    return db_path


def _ensure_on_sys_path(path: Path) -> None:
    """Prepend ``path`` to ``sys.path`` when it is not already present."""
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)


def discover_frameworks(src_dir: Path = SRC_DIR) -> list[FrameworkSpec]:
    """Find framework folders that contain an ``agent.py`` module.

    Args:
        src_dir: Directory that contains framework packages.

    Returns:
        Sorted list of discovered framework specs.
    """
    frameworks: list[FrameworkSpec] = []
    if not src_dir.is_dir():
        return frameworks
    for child in sorted(src_dir.iterdir(), key=lambda item: item.name.lower()):
        if not child.is_dir() or child.name in _SKIP_DIR_NAMES or child.name.startswith("."):
            continue
        if not (child / "agent.py").is_file():
            continue
        display_name = _FRAMEWORK_LABELS.get(child.name, child.name.replace("-", " ").title())
        frameworks.append(FrameworkSpec(name=child.name, path=child, display_name=display_name))
    return frameworks


def load_framework_agent_module(framework_dir: Path) -> ModuleType:
    """Load ``agent.py`` from a framework folder, including hyphenated names.

    Hyphenated folders are not valid Python package names, so the module is
    loaded from the file path. The framework directory is placed on
    ``sys.path`` so intra-package imports such as ``from state import ...``
    continue to work.

    Args:
        framework_dir: Folder that contains ``agent.py``.

    Returns:
        The loaded agent module.

    Raises:
        FileNotFoundError: If ``agent.py`` is missing.
        ImportError: If the module cannot be loaded.
    """
    agent_file = framework_dir / "agent.py"
    if not agent_file.is_file():
        raise FileNotFoundError(f"No agent.py in {framework_dir}")

    _ensure_on_sys_path(framework_dir)
    _ensure_on_sys_path(framework_dir.parent)

    resolved = framework_dir.resolve()
    module_name = f"ui_agent_{framework_dir.name.replace('-', '_')}_{abs(hash(str(resolved)))}"
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


def invoke_framework_agent(framework_dir: Path, question: str) -> dict[str, Any]:
    """Run a framework agent and return the answer plus optional query history.

    Prefers the compiled graph when ``get_compiled_agent`` exists so the UI can
    show SQL history. Falls back to ``ask(question)``.

    Args:
        framework_dir: Framework folder containing ``agent.py``.
        question: User question to send to the agent.

    Returns:
        Dictionary with ``final_answer``, ``blocked``, ``intent_reason``, and
        ``query_history``.

    Raises:
        AttributeError: If the module exposes neither entry point.
        ValueError: If ``question`` is empty.
    """
    stripped = question.strip()
    if not stripped:
        raise ValueError("Question must not be empty.")

    module = load_framework_agent_module(framework_dir)
    get_compiled = getattr(module, "get_compiled_agent", None)
    if callable(get_compiled):
        result = get_compiled().invoke(
            {"user_question": stripped, "messages": [HumanMessage(content=stripped)]}
        )
        return {
            "final_answer": result.get("final_answer") or "",
            "blocked": bool(result.get("blocked")),
            "intent_reason": result.get("intent_reason"),
            "query_history": result.get("query_history") or [],
        }

    ask_fn = getattr(module, "ask", None)
    if callable(ask_fn):
        return {
            "final_answer": ask_fn(stripped) or "",
            "blocked": False,
            "intent_reason": None,
            "query_history": [],
        }

    raise AttributeError(
        f"{framework_dir.name} agent.py must expose ask() or get_compiled_agent()."
    )


def _render_query_history(history: list[dict[str, Any]]) -> None:
    """Show executed SQL statements and sample rows in an expander."""
    if not history:
        return
    with st.expander("Query history", expanded=False):
        for index, record in enumerate(history, start=1):
            st.markdown(f"**Query {index}**")
            sql = record.get("sql") or ""
            if sql:
                st.code(sql, language="sql")
            error = record.get("error")
            if error:
                st.error(error)
            rows = record.get("rows") or []
            if rows:
                st.dataframe(rows, use_container_width=True)


def render_app(src_dir: Path = SRC_DIR) -> None:
    """Render the Streamlit chat UI for the selected framework agent."""
    st.set_page_config(page_title="E-commerce Analytics Agents", layout="wide")
    st.title("E-commerce Analytics Assistant")
    st.caption("Ask read-only questions about sales, customers, products, orders, and engagement.")

    frameworks = discover_frameworks(src_dir)
    if not frameworks:
        st.error("No framework agents found under src/. Expected a folder with agent.py.")
        return

    options = {item.name: item for item in frameworks}
    with st.sidebar:
        st.header("Agent")
        selected_name = st.selectbox(
            "Framework",
            options=list(options.keys()),
            format_func=lambda name: f"{options[name].display_name} ({name})",
        )
        st.caption("Each option maps to a framework folder under src/.")
        if st.button("Clear conversation"):
            st.session_state[f"messages_{selected_name}"] = []
            st.rerun()

    selected = options[selected_name]
    chat_key = f"messages_{selected.name}"
    if chat_key not in st.session_state:
        st.session_state[chat_key] = []

    for message in st.session_state[chat_key]:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if message.get("query_history"):
                _render_query_history(message["query_history"])

    prompt = st.chat_input("Ask about revenue, customers, products, or orders")
    if not prompt:
        return

    st.session_state[chat_key].append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        try:
            with st.spinner(f"Running {selected.display_name} agent..."):
                result = invoke_framework_agent(selected.path, prompt)
            answer = result["final_answer"] or "The agent returned an empty answer."
            st.markdown(answer)
            _render_query_history(result["query_history"])
            st.session_state[chat_key].append(
                {
                    "role": "assistant",
                    "content": answer,
                    "query_history": result["query_history"],
                }
            )
        except Exception as exc:  # noqa: BLE001 - shown in the chat pane
            logger.exception("Agent invocation failed for %s", selected.name)
            error_text = f"The agent failed: {exc}"
            st.error(error_text)
            st.session_state[chat_key].append({"role": "assistant", "content": error_text})


def main() -> int:
    """Streamlit entry point."""
    try:
        configure_logging()
        configure_environment()
        render_app()
        return EXIT_SUCCESS
    except KeyboardInterrupt:
        print("\nInterrupted by user", file=sys.stderr)
        return 130
    except Exception as exc:  # noqa: BLE001 - top-level UI failure
        logger.exception("UI failed: %s", exc)
        return EXIT_FAILURE


if __name__ == "__main__":
    sys.exit(main())

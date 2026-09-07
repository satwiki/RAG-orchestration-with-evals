#!/usr/bin/env python3
"""Run pytest for framework code changed during an agent session."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

EXIT_SUCCESS = 0

FRAMEWORKS = {"langgraph", "maf"}
PYTEST_NO_TESTS_COLLECTED = 5


def framework_for_path(path: Path, workspace: Path) -> str | None:
    """Return the framework represented by a source or test path."""
    parts = path.relative_to(workspace).parts
    if len(parts) >= 2 and parts[0] == "src" and parts[1] in FRAMEWORKS:
        return parts[1]
    if parts and parts[0] == "tests":
        return next((name for name in FRAMEWORKS if name in parts), None)
    return None


def framework_snapshot(workspace: Path) -> dict[str, str]:
    """Hash framework source and test files for session change detection."""
    snapshot: dict[str, str] = {}
    for root_name in ("src", "tests"):
        root = workspace / root_name
        if not root.exists():
            continue
        for path in root.rglob("*.py"):
            if framework_for_path(path, workspace):
                relative_path = path.relative_to(workspace).as_posix()
                snapshot[relative_path] = hashlib.sha256(path.read_bytes()).hexdigest()
    return snapshot


def snapshot_path(workspace: Path, session_id: str) -> Path:
    """Return a temporary snapshot path unique to the workspace and session."""
    identity = hashlib.sha256(f"{workspace.resolve()}:{session_id}".encode()).hexdigest()
    return Path(tempfile.gettempdir()) / "vscode-framework-test-hooks" / f"{identity}.json"


def save_snapshot(workspace: Path, session_id: str) -> None:
    """Persist the initial framework file hashes for this session."""
    path = snapshot_path(workspace, session_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(framework_snapshot(workspace)), encoding="utf-8")


def changed_frameworks(workspace: Path, session_id: str) -> set[str]:
    """Compare current framework files with the session-start snapshot."""
    path = snapshot_path(workspace, session_id)
    if not path.exists():
        return set()

    original = json.loads(path.read_text(encoding="utf-8"))
    current = framework_snapshot(workspace)
    changed_paths = {
        relative_path
        for relative_path in original.keys() | current.keys()
        if original.get(relative_path) != current.get(relative_path)
    }
    return {
        framework
        for relative_path in changed_paths
        if (framework := framework_for_path(workspace / relative_path, workspace))
    }


def test_directories(workspace: Path, frameworks: set[str]) -> list[Path]:
    """Find existing test directories named for affected frameworks."""
    tests_root = workspace / "tests"
    return sorted(
        path
        for path in tests_root.rglob("*")
        if path.is_dir() and path.name in frameworks
    )


def emit_stop_result(message: str, *, block: bool = False) -> int:
    """Write a valid Stop response."""
    output: dict[str, object] = {"systemMessage": message}
    if block:
        output["hookSpecificOutput"] = {
            "hookEventName": "Stop",
            "decision": "block",
            "reason": message,
        }
    print(json.dumps(output))
    return EXIT_SUCCESS


def run() -> int:
    """Capture session state or run framework-scoped tests at stop."""
    payload = json.load(sys.stdin)
    workspace = Path(payload.get("cwd") or Path.cwd())
    session_id = str(payload.get("session_id") or "default")
    event_name = payload.get("hook_event_name")

    if event_name == "SessionStart":
        save_snapshot(workspace, session_id)
        return EXIT_SUCCESS

    if event_name != "Stop":
        return EXIT_SUCCESS

    frameworks = changed_frameworks(workspace, session_id)
    if not frameworks:
        return EXIT_SUCCESS

    directories = test_directories(workspace, frameworks)
    framework_names = ", ".join(sorted(frameworks))
    if not directories:
        return emit_stop_result(
            f"No framework-specific test directory exists for: {framework_names}."
        )

    command = [sys.executable, "-m", "pytest", *map(str, directories)]
    result = subprocess.run(
        command,
        cwd=workspace,
        capture_output=True,
        text=True,
        check=False,
    )
    output = "\n".join(part.strip() for part in (result.stdout, result.stderr) if part.strip())
    if result.returncode == PYTEST_NO_TESTS_COLLECTED:
        return emit_stop_result(
            f"Pytest collected no tests for {framework_names}:\n{output[-2000:]}"
        )
    if result.returncode != 0:
        return emit_stop_result(
            f"Framework tests failed for {framework_names}:\n{output[-6000:]}",
            block=not bool(payload.get("stop_hook_active")),
        )

    return EXIT_SUCCESS


def main() -> int:
    """Run the hook with top-level error handling."""
    try:
        return run()
    except (json.JSONDecodeError, OSError, subprocess.SubprocessError) as error:
        return emit_stop_result(f"Framework test hook failed: {error}", block=True)


if __name__ == "__main__":
    sys.exit(main())
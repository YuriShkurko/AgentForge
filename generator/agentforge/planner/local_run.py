"""Safe local Builder run lifecycle for serve-builder.

This module intentionally exposes only a bounded validate/generate/validate-app
sequence for the Builder UI. It never accepts arbitrary commands or output paths
from the browser.
"""
from __future__ import annotations

import os
import re
import subprocess
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from agentforge.blueprints import blueprint_to_yaml
from agentforge.generator import generate
from agentforge.pack import DomainPack
from agentforge.planner import validate_blueprint_result


_RUN_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{7,63}$")
_MAX_LOG_CHARS = 12000
_DEFAULT_TIMEOUT_SECONDS = 120


@dataclass(frozen=True)
class LocalRunPaths:
    """Resolved safe paths for one Builder local run."""

    root: Path
    run_id: str
    run_dir: Path
    blueprint_path: Path
    app_dir: Path


def builder_runs_root(repo_root: Path | None = None) -> Path:
    """Return the only directory where Builder local runs may write."""
    root = repo_root or Path(__file__).resolve().parents[3]
    return root / ".tmp" / "builder-runs"


def make_run_id() -> str:
    """Create a server-side run id with no user-controlled path content."""
    return f"run-{uuid.uuid4().hex[:12]}"


def safe_run_paths(run_id: str, *, repo_root: Path | None = None) -> LocalRunPaths:
    """Resolve run paths and reject traversal or malformed ids."""
    if not isinstance(run_id, str) or not _RUN_ID_RE.match(run_id):
        raise ValueError("invalid local run id")
    root = builder_runs_root(repo_root).resolve()
    run_dir = (root / run_id).resolve()
    try:
        run_dir.relative_to(root)
    except ValueError as exc:  # pragma: no cover - defensive after regex
        raise ValueError("local run path escaped builder-runs root") from exc
    return LocalRunPaths(
        root=root,
        run_id=run_id,
        run_dir=run_dir,
        blueprint_path=run_dir / "domain-pack.yaml",
        app_dir=run_dir / "app",
    )


def validate_blueprint_for_local_run(blueprint: dict[str, Any] | None) -> dict[str, Any]:
    """Validate the active Builder Blueprint without writing files."""
    result = validate_blueprint_result(blueprint, path=".tmp/builder-runs/<run-id>/domain-pack.yaml")
    return {
        "step": "validate-blueprint",
        "ok": result.status == "draft",
        "status": "success" if result.status == "draft" else "error",
        "exit_code": 0 if result.status == "draft" else 1,
        "errors": result.errors,
        "warnings": result.warnings,
        "commands": ["agentforge plan .tmp/builder-runs/<run-id>/domain-pack.yaml"],
        "blueprint": result.blueprint,
        "yaml": result.yaml,
        "stdout": "Blueprint schema validation passed." if result.status == "draft" else "",
        "stderr": "\n".join(result.errors),
    }


def generate_local_app(blueprint: dict[str, Any] | None, *, repo_root: Path | None = None) -> dict[str, Any]:
    """Generate the active Blueprint into .tmp/builder-runs/<run-id>/app."""
    validation = validate_blueprint_for_local_run(blueprint)
    if not validation["ok"]:
        return {**validation, "step": "generate", "status": "error"}
    pack = DomainPack.model_validate(blueprint)
    paths = safe_run_paths(make_run_id(), repo_root=repo_root)
    paths.run_dir.mkdir(parents=True, exist_ok=False)
    paths.blueprint_path.write_text(blueprint_to_yaml(blueprint or {}), encoding="utf-8")
    try:
        manifest = generate(pack, paths.app_dir)
    except Exception as exc:
        return {
            "step": "generate",
            "ok": False,
            "status": "error",
            "exit_code": 1,
            "run_id": paths.run_id,
            "run_dir": _display_path(paths.run_dir, repo_root),
            "blueprint_path": _display_path(paths.blueprint_path, repo_root),
            "generated_path": _display_path(paths.app_dir, repo_root),
            "commands": [_generate_command(paths, repo_root)],
            "stdout": "",
            "stderr": _truncate_log(f"generation failed: {exc}"),
            "errors": [f"generation failed: {exc}"],
        }
    return {
        "step": "generate",
        "ok": True,
        "status": "success",
        "exit_code": 0,
        "run_id": paths.run_id,
        "run_dir": _display_path(paths.run_dir, repo_root),
        "blueprint_path": _display_path(paths.blueprint_path, repo_root),
        "generated_path": _display_path(paths.app_dir, repo_root),
        "manifest": manifest,
        "commands": [_generate_command(paths, repo_root)],
        "stdout": f"Generated {pack.display_name} into {_display_path(paths.app_dir, repo_root)}.",
        "stderr": "",
        "errors": [],
    }


def validate_generated_app(run_id: str, *, repo_root: Path | None = None, timeout_seconds: int = _DEFAULT_TIMEOUT_SECONDS) -> dict[str, Any]:
    """Run the fixed generated-app validation command for a safe run id."""
    paths = safe_run_paths(run_id, repo_root=repo_root)
    if not paths.app_dir.exists():
        return _validate_app_error(paths, repo_root, "generated app path does not exist")
    if not (paths.app_dir / "Makefile").exists():
        return _validate_app_error(paths, repo_root, "generated app has no Makefile")
    result = _run_allowlisted_command(["make", "validate"], cwd=paths.app_dir, timeout_seconds=timeout_seconds)
    return {
        "step": "validate-app",
        "ok": result["exit_code"] == 0,
        "status": "success" if result["exit_code"] == 0 else "error",
        "exit_code": result["exit_code"],
        "run_id": paths.run_id,
        "run_dir": _display_path(paths.run_dir, repo_root),
        "generated_path": _display_path(paths.app_dir, repo_root),
        "commands": ["cd " + _display_path(paths.app_dir, repo_root), "make validate"],
        "stdout": result["stdout"],
        "stderr": result["stderr"],
        "timed_out": result.get("timed_out", False),
        "truncated": result.get("truncated", False),
        "errors": [] if result["exit_code"] == 0 else ["make validate failed"],
    }


def _validate_app_error(paths: LocalRunPaths, repo_root: Path | None, message: str) -> dict[str, Any]:
    return {
        "step": "validate-app",
        "ok": False,
        "status": "error",
        "exit_code": 1,
        "run_id": paths.run_id,
        "run_dir": _display_path(paths.run_dir, repo_root),
        "generated_path": _display_path(paths.app_dir, repo_root),
        "commands": ["cd " + _display_path(paths.app_dir, repo_root), "make validate"],
        "stdout": "",
        "stderr": message,
        "errors": [message],
    }


def _run_allowlisted_command(command: list[str], *, cwd: Path, timeout_seconds: int) -> dict[str, Any]:
    if command != ["make", "validate"]:
        raise ValueError("command is not allowlisted")
    try:
        proc = subprocess.run(
            command,
            cwd=cwd,
            shell=False,
            text=True,
            capture_output=True,
            timeout=timeout_seconds,
            env=_safe_subprocess_env(),
            check=False,
        )
        stdout, stdout_truncated = _truncate_log_with_flag(proc.stdout or "")
        stderr, stderr_truncated = _truncate_log_with_flag(proc.stderr or "")
        return {
            "exit_code": proc.returncode,
            "stdout": stdout,
            "stderr": stderr,
            "truncated": stdout_truncated or stderr_truncated,
        }
    except subprocess.TimeoutExpired as exc:
        stdout, stdout_truncated = _truncate_log_with_flag(_decode_timeout_output(exc.stdout))
        stderr, stderr_truncated = _truncate_log_with_flag("make validate timed out\n" + _decode_timeout_output(exc.stderr))
        return {
            "exit_code": 124,
            "stdout": stdout,
            "stderr": stderr.strip(),
            "timed_out": True,
            "truncated": stdout_truncated or stderr_truncated,
        }
    except FileNotFoundError:
        return {"exit_code": 127, "stdout": "", "stderr": "make executable was not found", "truncated": False}


def _safe_subprocess_env() -> dict[str, str]:
    # Keep secrets out, but preserve ordinary OS/toolchain variables needed by
    # Python, GNU Make, npm, shells, and Windows runtime DLL/socket discovery.
    secret_markers = ("KEY", "TOKEN", "SECRET", "PASSWORD", "PASSWD", "CREDENTIAL", "COOKIE", "AUTH")
    env: dict[str, str] = {}
    for key, value in os.environ.items():
        upper = key.upper()
        if any(marker in upper for marker in secret_markers):
            continue
        env[key] = value
    return env


def _decode_timeout_output(value: str | bytes | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value


def _truncate_log(value: str) -> str:
    return _truncate_log_with_flag(value)[0]


def _truncate_log_with_flag(value: str) -> tuple[str, bool]:
    if len(value) <= _MAX_LOG_CHARS:
        return value, False
    marker = "\n...[log truncated]...\n"
    keep = max(0, _MAX_LOG_CHARS - len(marker))
    return value[:keep] + marker, True


def _generate_command(paths: LocalRunPaths, repo_root: Path | None) -> str:
    return f"agentforge generate {_display_path(paths.blueprint_path, repo_root)} --output {_display_path(paths.app_dir, repo_root)}"


def _display_path(path: Path, repo_root: Path | None) -> str:
    base = (repo_root or Path(__file__).resolve().parents[3]).resolve()
    resolved = path.resolve()
    try:
        return resolved.relative_to(base).as_posix()
    except ValueError:
        return str(resolved)


__all__ = [
    "builder_runs_root",
    "generate_local_app",
    "make_run_id",
    "safe_run_paths",
    "validate_blueprint_for_local_run",
    "validate_generated_app",
]

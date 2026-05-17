"""Local builder server for the scripted App Blueprint planner."""
from __future__ import annotations

import json
import os
import re
import subprocess
from dataclasses import dataclass, field
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from agentforge.planner import PlannerResult, validate_blueprint_result
from agentforge.planner.assistant import BuilderAssistant
from agentforge.planner.local_run import generate_local_app, validate_blueprint_for_local_run, validate_generated_app
from agentforge.planner.scripted import ScriptedPlanner


_ENV_KEY_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


@dataclass
class DotenvLoadResult:
    """Non-secret summary of a local builder .env load attempt."""

    path: Path
    existed: bool = False
    loaded_keys: list[str] = field(default_factory=list)
    skipped_existing_keys: list[str] = field(default_factory=list)
    malformed_lines: int = 0
    git_ignored: bool | None = None
    warning: str = ""


class PlannerServer(ThreadingHTTPServer):
    """HTTP server that serves the static builder and planner endpoints."""

    def __init__(
        self,
        server_address: tuple[str, int],
        builder_dir: Path,
        *,
        assistant: BuilderAssistant | None = None,
    ):
        self.builder_dir = builder_dir
        self.planner = ScriptedPlanner()
        self.assistant = assistant if assistant is not None else BuilderAssistant.from_env()
        super().__init__(server_address, PlannerRequestHandler)


class PlannerRequestHandler(SimpleHTTPRequestHandler):
    """Serve builder assets plus a minimal JSON planner API."""

    server: PlannerServer

    def __init__(self, request: Any, client_address: Any, server: PlannerServer):
        super().__init__(request, client_address, server, directory=str(server.builder_dir))

    def end_headers(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Cache-Control", "no-store, max-age=0")
        super().end_headers()

    def do_OPTIONS(self) -> None:  # noqa: N802
        self.send_response(HTTPStatus.NO_CONTENT)
        self.end_headers()

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/api/planner/status":
            assistant = self.server.assistant
            self._write_json({
                "mode": assistant.mode,
                "planner_available": True,
                "live_provider": assistant.live_provider_enabled,
            })
            return
        super().do_GET()

    def do_POST(self) -> None:  # noqa: N802
        try:
            payload = self._read_json()
            if self.path == "/api/planner/draft":
                result = self.server.planner.draft(
                    str(payload.get("idea") or ""),
                    _string_map(payload.get("prior_answers")),
                )
                self._write_planner_result(result)
            elif self.path == "/api/planner/clarify":
                result = self.server.planner.clarify(str(payload.get("idea") or ""))
                self._write_planner_result(result)
            elif self.path == "/api/planner/refine":
                result = self.server.planner.refine(
                    payload.get("blueprint") if isinstance(payload.get("blueprint"), dict) else {},
                    str(payload.get("instruction") or ""),
                )
                self._write_planner_result(result)
            elif self.path == "/api/planner/validate":
                result = validate_blueprint_result(
                    payload.get("blueprint") if isinstance(payload.get("blueprint"), dict) else None,
                    path=str(payload.get("path") or "./domain-packs/draft/domain-pack.yaml"),
                )
                self._write_planner_result(result)
            elif self.path == "/api/planner/assistant/start":
                self._write_json(self.server.assistant.start(
                    str(payload.get("idea") or ""),
                    _optional_dict(payload.get("current_blueprint")),
                ))
            elif self.path == "/api/planner/assistant/message":
                self._write_json(self.server.assistant.message(
                    _optional_dict(payload.get("state")),
                    str(payload.get("message") or ""),
                    _optional_dict(payload.get("current_blueprint")),
                ))
            elif self.path == "/api/planner/assistant/apply-preview":
                self._write_json(self.server.assistant.apply_preview(_optional_dict(payload.get("proposal"))))
            elif self.path == "/api/planner/local-run/validate-blueprint":
                self._write_json(validate_blueprint_for_local_run(_optional_dict(payload.get("blueprint"))))
            elif self.path == "/api/planner/local-run/generate":
                self._write_json(generate_local_app(_optional_dict(payload.get("blueprint"))))
            elif self.path == "/api/planner/local-run/validate-app":
                self._write_json(validate_generated_app(str(payload.get("run_id") or "")))
            else:
                self._write_json({"error": "unknown planner endpoint"}, HTTPStatus.NOT_FOUND)
                return
        except Exception as exc:
            self._write_planner_result(PlannerResult(status="error", errors=[str(exc)]), HTTPStatus.BAD_REQUEST)

    def _read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length") or 0)
        if length == 0:
            return {}
        raw = self.rfile.read(length).decode("utf-8")
        data = json.loads(raw)
        return data if isinstance(data, dict) else {}

    def _write_planner_result(self, result: PlannerResult, status: HTTPStatus = HTTPStatus.OK) -> None:
        self._write_json(result.to_dict(), status)

    def _write_json(self, payload: dict[str, Any], status: HTTPStatus = HTTPStatus.OK) -> None:
        data = json.dumps(payload, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, format: str, *args: Any) -> None:
        return


def _string_map(value: Any) -> dict[str, str] | None:
    if not isinstance(value, dict):
        return None
    return {str(key): str(item) for key, item in value.items() if str(item).strip()}


def _optional_dict(value: Any) -> dict[str, Any] | None:
    return value if isinstance(value, dict) else None


def _parse_dotenv_line(line: str) -> tuple[str, str] | None:
    stripped = line.strip()
    if not stripped or stripped.startswith("#") or "=" not in stripped:
        return None
    key, value = stripped.split("=", 1)
    key = key.strip()
    if not _ENV_KEY_RE.match(key):
        return None
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        value = value[1:-1]
    return key, value


def _env_file_is_git_ignored(env_path: Path) -> bool | None:
    try:
        proc = subprocess.run(
            ["git", "check-ignore", "--quiet", env_path.name],
            cwd=env_path.parent,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
    except Exception:
        return None
    if proc.returncode == 0:
        return True
    if proc.returncode == 1:
        return False
    return None


def load_builder_dotenv(env_path: Path | None = None, *, environ: dict[str, str] | None = None) -> DotenvLoadResult:
    """Load local ``.env`` values for ``agentforge serve-builder`` only.

    Existing environment variables win. Returned metadata contains only keys,
    counts, and safety flags; values are never logged or exposed.
    """
    target = env_path or Path.cwd() / ".env"
    env = environ if environ is not None else os.environ
    result = DotenvLoadResult(path=target)
    if not target.exists():
        return result
    result.existed = True
    result.git_ignored = _env_file_is_git_ignored(target)
    if result.git_ignored is False:
        result.warning = f"Warning: local .env exists at {target} but is not ignored by git. Do not commit secrets."
    try:
        lines = target.read_text(encoding="utf-8").splitlines()
    except Exception:
        result.malformed_lines += 1
        return result
    for line in lines:
        if line.strip() and not line.strip().startswith("#") and "=" not in line:
            result.malformed_lines += 1
            continue
        parsed = _parse_dotenv_line(line)
        if parsed is None:
            if line.strip() and not line.strip().startswith("#") and "=" in line:
                result.malformed_lines += 1
            continue
        key, value = parsed
        if key in env:
            result.skipped_existing_keys.append(key)
            continue
        env[key] = value
        result.loaded_keys.append(key)
    return result


def create_builder_server(
    host: str = "127.0.0.1",
    port: int = 8765,
    builder_dir: Path | None = None,
    *,
    load_env: bool = True,
) -> tuple[PlannerServer, DotenvLoadResult | None]:
    """Create the local builder server, optionally loading cwd/.env first."""
    root = Path(__file__).resolve().parents[3]
    resolved_builder_dir = builder_dir or root / "builder"
    env_result = load_builder_dotenv() if load_env else None
    server = PlannerServer((host, port), resolved_builder_dir)
    return server, env_result


def serve_builder(host: str = "127.0.0.1", port: int = 8765, builder_dir: Path | None = None) -> None:
    """Serve the static builder with scripted planner endpoints."""
    server, env_result = create_builder_server(host, port, builder_dir)
    print(f"Serving AgentForge builder at http://{host}:{port}/")
    print(f"Builder assets: {server.builder_dir}")
    if env_result and env_result.warning:
        print(env_result.warning)
    if env_result and env_result.existed:
        loaded = len(env_result.loaded_keys)
        skipped = len(env_result.skipped_existing_keys)
        malformed = env_result.malformed_lines
        print(f"Loaded local .env for builder server: {loaded} variable(s), {skipped} already set, {malformed} ignored malformed line(s).")
    print("Planner mode: scripted")
    print(f"Builder Assistant mode: {server.assistant.mode}")
    server.serve_forever()


__all__ = [
    "DotenvLoadResult",
    "PlannerRequestHandler",
    "PlannerServer",
    "create_builder_server",
    "load_builder_dotenv",
    "serve_builder",
]

"""Local builder server for the scripted App Blueprint planner."""
from __future__ import annotations

import json
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from agentforge.planner import PlannerResult, validate_blueprint_result
from agentforge.planner.scripted import ScriptedPlanner


class PlannerServer(ThreadingHTTPServer):
    """HTTP server that serves the static builder and planner endpoints."""

    def __init__(self, server_address: tuple[str, int], builder_dir: Path):
        self.builder_dir = builder_dir
        self.planner = ScriptedPlanner()
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
        super().end_headers()

    def do_OPTIONS(self) -> None:  # noqa: N802
        self.send_response(HTTPStatus.NO_CONTENT)
        self.end_headers()

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/api/planner/status":
            self._write_json({
                "mode": "scripted",
                "planner_available": True,
                "live_provider": False,
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
            elif self.path == "/api/planner/clarify":
                result = self.server.planner.clarify(str(payload.get("idea") or ""))
            elif self.path == "/api/planner/refine":
                result = self.server.planner.refine(
                    payload.get("blueprint") if isinstance(payload.get("blueprint"), dict) else {},
                    str(payload.get("instruction") or ""),
                )
            elif self.path == "/api/planner/validate":
                result = validate_blueprint_result(
                    payload.get("blueprint") if isinstance(payload.get("blueprint"), dict) else None,
                    path=str(payload.get("path") or "./domain-packs/draft/domain-pack.yaml"),
                )
            else:
                self._write_json({"error": "unknown planner endpoint"}, HTTPStatus.NOT_FOUND)
                return
            self._write_planner_result(result)
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


def serve_builder(host: str = "127.0.0.1", port: int = 8765, builder_dir: Path | None = None) -> None:
    """Serve the static builder with scripted planner endpoints."""
    root = Path(__file__).resolve().parents[3]
    resolved_builder_dir = builder_dir or root / "builder"
    server = PlannerServer((host, port), resolved_builder_dir)
    print(f"Serving AgentForge builder at http://{host}:{port}/")
    print("Planner mode: scripted")
    server.serve_forever()


__all__ = ["PlannerRequestHandler", "PlannerServer", "serve_builder"]

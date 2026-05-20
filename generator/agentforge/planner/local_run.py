"""Safe local Builder run lifecycle for serve-builder.

This module intentionally exposes only a bounded validate/generate/validate-app
sequence for the Builder UI. It never accepts arbitrary commands or output paths
from the browser.
"""
from __future__ import annotations

import os
import re
import signal
import socket
import subprocess
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from agentforge.blueprints import blueprint_to_yaml
from agentforge.generator import generate
from agentforge.pack import DomainPack
from agentforge.planner import validate_blueprint_result


_RUN_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{7,63}$")
_MAX_LOG_CHARS = 12000
_DEFAULT_TIMEOUT_SECONDS = 120
_SERVICE_SPECS = {
    "backend": {"target": "run-backend", "url": "http://127.0.0.1:8000/docs", "health_url": "http://127.0.0.1:8000/health"},
    "frontend": {"target": "run-frontend", "url": "http://localhost:5173", "health_url": "http://localhost:5173"},
}
_PROCESS_LOCK = threading.Lock()
_PROCESS_REGISTRY: dict[tuple[Path, str, str], "ManagedProcess"] = {}


@dataclass(frozen=True)
class LocalRunPaths:
    """Resolved safe paths for one Builder local run."""

    root: Path
    run_id: str
    run_dir: Path
    blueprint_path: Path
    app_dir: Path


@dataclass
class ManagedProcess:
    """One generated app process started by the Builder."""

    run_id: str
    service: str
    command: list[str]
    cwd: Path
    url: str
    proc: subprocess.Popen[str]
    started_at: float = field(default_factory=time.time)
    stdout: str = ""
    stderr: str = ""
    stdout_truncated: bool = False
    stderr_truncated: bool = False
    readiness_error: str = ""


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


def start_generated_app_service(run_id: str, service: str, *, repo_root: Path | None = None) -> dict[str, Any]:
    """Start one allowlisted generated-app service for a local run."""
    paths = safe_run_paths(run_id, repo_root=repo_root)
    spec = _service_spec(service)
    error = _service_preflight_error(paths, spec["target"], repo_root)
    if error:
        return _service_error(paths, service, spec, "start-service", error, repo_root)
    key = _process_key(paths, service)
    with _PROCESS_LOCK:
        existing = _PROCESS_REGISTRY.get(key)
        if existing and _process_running(existing.proc):
            return _service_status(paths, service, spec, "start-service", existing, repo_root, duplicate=True)
        if existing:
            _PROCESS_REGISTRY.pop(key, None)
        _stop_other_run_processes_locked(paths, service)
        port_error = _fixed_port_preflight_error(service, spec)
        if port_error:
            return _service_error(paths, service, spec, "start-service", port_error, repo_root)
        command = ["make", spec["target"]]
        try:
            proc = _popen_allowlisted_service(command, cwd=paths.app_dir)
        except Exception as exc:
            return _service_error(paths, service, spec, "start-service", f"failed to start {service}: {exc}", repo_root)
        managed = ManagedProcess(run_id=paths.run_id, service=service, command=command, cwd=paths.app_dir, url=spec["url"], proc=proc)
        _PROCESS_REGISTRY[key] = managed
        _capture_stream(managed, "stdout", proc.stdout)
        _capture_stream(managed, "stderr", proc.stderr)
        _wait_for_service_ready(managed, spec)
        return _service_status(paths, service, spec, "start-service", managed, repo_root)


def stop_generated_app_service(run_id: str, service: str, *, repo_root: Path | None = None) -> dict[str, Any]:
    """Stop one generated-app service previously started by the Builder."""
    paths = safe_run_paths(run_id, repo_root=repo_root)
    spec = _service_spec(service)
    key = _process_key(paths, service)
    with _PROCESS_LOCK:
        managed = _PROCESS_REGISTRY.get(key)
        if not managed:
            return _service_not_running(paths, service, spec, "stop-service", repo_root)
        _terminate_process_tree(managed.proc)
        _cleanup_builder_service_port(service, spec)
        _PROCESS_REGISTRY.pop(key, None)
        return _service_status(paths, service, spec, "stop-service", managed, repo_root, stopped=True)


def get_generated_app_service_status(run_id: str, service: str, *, repo_root: Path | None = None) -> dict[str, Any]:
    """Return current status for a Builder-started generated-app service."""
    paths = safe_run_paths(run_id, repo_root=repo_root)
    spec = _service_spec(service)
    managed = _PROCESS_REGISTRY.get(_process_key(paths, service))
    if not managed:
        return _service_not_running(paths, service, spec, "service-status", repo_root)
    return _service_status(paths, service, spec, "service-status", managed, repo_root)


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


def _popen_allowlisted_service(command: list[str], *, cwd: Path) -> subprocess.Popen[str]:
    allowed = [["make", spec["target"]] for spec in _SERVICE_SPECS.values()]
    if command not in allowed:
        raise ValueError("service command is not allowlisted")
    kwargs: dict[str, Any] = {}
    if os.name == "nt":
        kwargs["creationflags"] = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    else:
        kwargs["start_new_session"] = True
    env = _safe_subprocess_env()
    if command == ["make", "run-backend"]:
        # serve-builder may load a repo-level .env for the Builder itself. Generated
        # demos must still start with their local SQLite default unless the user
        # runs them manually and chooses a different environment.
        env["DATABASE_URL"] = "sqlite:///./app.db"
    return subprocess.Popen(
        command,
        cwd=cwd,
        shell=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        **kwargs,
    )


def _service_spec(service: str) -> dict[str, str]:
    if service not in _SERVICE_SPECS:
        raise ValueError("invalid local run service")
    return _SERVICE_SPECS[service]


def _service_preflight_error(paths: LocalRunPaths, target: str, repo_root: Path | None) -> str | None:
    if not paths.app_dir.exists():
        return "generated app path does not exist"
    makefile = paths.app_dir / "Makefile"
    if not makefile.exists():
        return "generated app has no Makefile"
    if not _makefile_has_target(makefile, target):
        return f"generated app Makefile has no {target} target"
    return None


def _makefile_has_target(makefile: Path, target: str) -> bool:
    pattern = re.compile(rf"^{re.escape(target)}\s*:")
    return any(pattern.match(line) for line in makefile.read_text(encoding="utf-8", errors="replace").splitlines())


def _process_key(paths: LocalRunPaths, service: str) -> tuple[Path, str, str]:
    return (paths.root, paths.run_id, service)


def _process_running(proc: subprocess.Popen[str]) -> bool:
    return proc.poll() is None


def _service_status(paths: LocalRunPaths, service: str, spec: dict[str, str], step: str, managed: ManagedProcess, repo_root: Path | None, *, duplicate: bool = False, stopped: bool = False) -> dict[str, Any]:
    running = _process_running(managed.proc) and not stopped
    exit_code = managed.proc.poll()
    ready = running and not managed.readiness_error and _url_available(spec["health_url"], timeout=0.5)
    if managed.readiness_error:
        status = "failed"
    else:
        status = "running" if ready else ("starting" if running else ("stopped" if stopped or exit_code is None else "failed"))
    stdout, stdout_truncated = _truncate_log_with_flag(managed.stdout)
    stderr, stderr_truncated = _truncate_log_with_flag(managed.stderr)
    return {
        "step": step,
        "ok": status in {"running", "starting", "stopped"},
        "status": status,
        "service": service,
        "run_id": paths.run_id,
        "run_dir": _display_path(paths.run_dir, repo_root),
        "generated_path": _display_path(paths.app_dir, repo_root),
        "url": spec["url"],
        "health_url": spec["health_url"],
        "commands": ["cd " + _display_path(paths.app_dir, repo_root), "make " + spec["target"]],
        "pid": managed.proc.pid,
        "exit_code": exit_code,
        "stdout": stdout,
        "stderr": stderr,
        "truncated": stdout_truncated or stderr_truncated or managed.stdout_truncated or managed.stderr_truncated,
        "duplicate": duplicate,
        "render_check": "passed" if service == "frontend" and status == "running" else ("failed" if service == "frontend" and managed.readiness_error else None),
        "errors": [] if status in {"running", "starting", "stopped"} else [managed.readiness_error or f"{service} process exited"],
    }


def _service_error(paths: LocalRunPaths, service: str, spec: dict[str, str], step: str, message: str, repo_root: Path | None) -> dict[str, Any]:
    return {
        "step": step,
        "ok": False,
        "status": "error",
        "service": service,
        "run_id": paths.run_id,
        "run_dir": _display_path(paths.run_dir, repo_root),
        "generated_path": _display_path(paths.app_dir, repo_root),
        "url": spec["url"],
        "commands": ["cd " + _display_path(paths.app_dir, repo_root), "make " + spec["target"]],
        "exit_code": 1,
        "stdout": "",
        "stderr": message,
        "errors": [message],
    }


def _service_not_running(paths: LocalRunPaths, service: str, spec: dict[str, str], step: str, repo_root: Path | None) -> dict[str, Any]:
    return {
        "step": step,
        "ok": True,
        "status": "stopped",
        "service": service,
        "run_id": paths.run_id,
        "run_dir": _display_path(paths.run_dir, repo_root),
        "generated_path": _display_path(paths.app_dir, repo_root),
        "url": spec["url"],
        "commands": ["cd " + _display_path(paths.app_dir, repo_root), "make " + spec["target"]],
        "exit_code": None,
        "stdout": "",
        "stderr": "",
        "errors": [],
    }


def _wait_for_service_ready(managed: ManagedProcess, spec: dict[str, str], timeout_seconds: float = 15.0) -> bool:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        if not _process_running(managed.proc):
            return False
        if _url_available(spec["health_url"], timeout=0.5):
            if managed.service == "frontend":
                ok, error = _frontend_render_check(managed.cwd, spec["health_url"], timeout=2.0)
                if not ok:
                    managed.readiness_error = error
                    return False
            return True
        time.sleep(0.25)
    return False


def _stop_other_run_processes_locked(paths: LocalRunPaths, service: str) -> None:
    for key, managed in list(_PROCESS_REGISTRY.items()):
        root, run_id, managed_service = key
        if root == paths.root and managed_service == service and run_id != paths.run_id:
            if _process_running(managed.proc):
                _terminate_process_tree(managed.proc)
            _PROCESS_REGISTRY.pop(key, None)


def _fixed_port_preflight_error(service: str, spec: dict[str, str]) -> str | None:
    if service != "frontend":
        return None
    parsed = urllib.parse.urlparse(spec["url"])
    host = parsed.hostname or "127.0.0.1"
    port = parsed.port
    if not port or _tcp_port_available(host, port):
        return None
    listening_pids = _listening_pids(port)
    if listening_pids and all(_is_builder_run_process(pid) for pid in listening_pids):
        _cleanup_builder_service_port(service, spec)
        deadline = time.time() + 5.0
        while time.time() < deadline:
            if _tcp_port_available(host, port):
                return None
            time.sleep(0.1)
        return f"Frontend port {port} is still held by a previous Builder-started generated app. Stop it or restart serve-builder."
    return f"Frontend port {port} is already in use by another process. Stop it or restart serve-builder."


def _cleanup_builder_service_port(service: str, spec: dict[str, str]) -> None:
    if service != "frontend":
        return
    parsed = urllib.parse.urlparse(spec["url"])
    port = parsed.port
    if not port:
        return
    for pid in _listening_pids(port):
        if _is_builder_run_process(pid):
            _terminate_pid_tree(pid)


def _tcp_port_available(host: str, port: int) -> bool:
    candidates = [host]
    if host == "localhost":
        candidates = ["127.0.0.1", "::1"]
    for candidate in candidates:
        family = socket.AF_INET6 if ":" in candidate else socket.AF_INET
        with socket.socket(family, socket.SOCK_STREAM) as sock:
            try:
                sock.bind((candidate, port))
            except OSError:
                return False
    return True


def _listening_pids(port: int) -> set[int]:
    if os.name == "nt":
        try:
            result = subprocess.run(["netstat", "-ano"], text=True, capture_output=True, timeout=5, check=False)
        except Exception:
            return set()
        pids: set[int] = set()
        marker = f":{port}"
        for line in result.stdout.splitlines():
            columns = line.split()
            if len(columns) >= 5 and columns[0].upper() == "TCP" and columns[1].endswith(marker) and columns[3].upper() == "LISTENING":
                try:
                    pids.add(int(columns[4]))
                except ValueError:
                    pass
        return pids
    try:
        result = subprocess.run(["lsof", "-nP", f"-iTCP:{port}", "-sTCP:LISTEN", "-t"], text=True, capture_output=True, timeout=5, check=False)
    except Exception:
        return set()
    pids: set[int] = set()
    for line in result.stdout.splitlines():
        try:
            pids.add(int(line.strip()))
        except ValueError:
            pass
    return pids


def _is_builder_run_process(pid: int) -> bool:
    command_line = _process_command_line(pid).replace("\\", "/").lower()
    return "/.tmp/builder-runs/" in command_line and ("vite" in command_line or "run-frontend" in command_line or "node" in command_line)


def _process_command_line(pid: int) -> str:
    if os.name == "nt":
        try:
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command", f"(Get-CimInstance Win32_Process -Filter 'ProcessId={pid}').CommandLine"],
                text=True,
                capture_output=True,
                timeout=5,
                check=False,
            )
            return result.stdout.strip()
        except Exception:
            return ""
    try:
        return Path(f"/proc/{pid}/cmdline").read_text(encoding="utf-8", errors="replace").replace("\x00", " ")
    except Exception:
        return ""


def _terminate_pid_tree(pid: int) -> None:
    try:
        if os.name == "nt":
            subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], capture_output=True, text=True, timeout=10, check=False)
        else:
            os.kill(pid, signal.SIGTERM)
    except Exception:
        pass


def _frontend_render_check(app_dir: Path, url: str, *, timeout: float) -> tuple[bool, str]:
    html, error = _fetch_text(url, timeout=timeout)
    if error:
        return False, error
    if not html.strip():
        return False, "frontend render check failed: blank response"
    expected_title = _expected_frontend_title(app_dir)
    if expected_title and expected_title not in html:
        return False, f"frontend render check failed: expected generated app title {expected_title!r} was not served"
    if '<div id="root"' not in html and "<div id='root'" not in html:
        return False, "frontend render check failed: Vite root element was not served"
    return True, ""


def _expected_frontend_title(app_dir: Path) -> str:
    index = app_dir / "frontend" / "index.html"
    if not index.exists():
        return ""
    html = index.read_text(encoding="utf-8", errors="replace")
    match = re.search(r"<title>(.*?)</title>", html, flags=re.IGNORECASE | re.DOTALL)
    return re.sub(r"\s+", " ", match.group(1)).strip() if match else ""


def _fetch_text(url: str, *, timeout: float) -> tuple[str, str]:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            status = getattr(response, "status", 0)
            if not 200 <= status < 400:
                return "", f"frontend render check failed: HTTP {status}"
            content_type = response.headers.get("Content-Type", "")
            if "html" not in content_type.lower() and content_type:
                return "", f"frontend render check failed: expected HTML but got {content_type}"
            return response.read(200000).decode("utf-8", errors="replace"), ""
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return "", f"frontend render check failed: {exc}"


def _url_available(url: str, *, timeout: float) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            return 200 <= response.status < 500
    except (urllib.error.URLError, TimeoutError, OSError):
        return False


def _capture_stream(managed: ManagedProcess, stream_name: str, stream: Any) -> None:
    if stream is None:
        return

    def reader() -> None:
        for chunk in iter(stream.readline, ""):
            with _PROCESS_LOCK:
                current = getattr(managed, stream_name)
                next_value, truncated = _truncate_log_with_flag(current + chunk)
                setattr(managed, stream_name, next_value)
                if truncated:
                    setattr(managed, f"{stream_name}_truncated", True)
        try:
            stream.close()
        except Exception:
            pass

    threading.Thread(target=reader, daemon=True).start()


def _terminate_process_tree(proc: subprocess.Popen[str]) -> None:
    if proc.poll() is not None:
        return
    try:
        if os.name == "nt":
            subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"], capture_output=True, text=True, timeout=10, check=False)
        else:
            os.killpg(proc.pid, signal.SIGTERM)
        proc.wait(timeout=10)
    except Exception:
        try:
            if os.name == "nt":
                proc.kill()
            else:
                os.killpg(proc.pid, signal.SIGKILL)
        except Exception:
            pass


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
    "get_generated_app_service_status",
    "generate_local_app",
    "make_run_id",
    "safe_run_paths",
    "start_generated_app_service",
    "stop_generated_app_service",
    "validate_blueprint_for_local_run",
    "validate_generated_app",
]

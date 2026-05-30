"""Tests for Builder Local Control Room safe local runs."""
import io
import json
import subprocess
import sys
import threading
import urllib.error
import urllib.request
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "generator"))

import agentforge.planner.local_run as local_run
import agentforge.planner.server as planner_server
from agentforge.planner.assistant import BuilderAssistant
from agentforge.planner.server import PlannerServer


def _coach_blueprint():
    result = BuilderAssistant().start("i am a basketball coach, want to track clients and court vendors")
    return result["proposal"]["blueprint"]


def test_safe_run_paths_reject_path_traversal(tmp_path):
    for run_id in ("../escape", "run/escape", "run-..", "", "C:/escape"):
        with pytest.raises(ValueError):
            local_run.safe_run_paths(run_id, repo_root=tmp_path)


def test_safe_run_paths_stay_under_builder_runs(tmp_path):
    paths = local_run.safe_run_paths("run-abc12345", repo_root=tmp_path)

    assert paths.run_dir == (tmp_path / ".tmp" / "builder-runs" / "run-abc12345").resolve()
    assert paths.blueprint_path.parent == paths.run_dir
    assert paths.app_dir.parent == paths.run_dir
    assert paths.run_dir.resolve().is_relative_to((tmp_path / ".tmp" / "builder-runs").resolve())


def test_validate_blueprint_success_and_failure():
    success = local_run.validate_blueprint_for_local_run(_coach_blueprint())
    failure = local_run.validate_blueprint_for_local_run({"name": "bad"})

    assert success["ok"] is True
    assert success["step"] == "validate-blueprint"
    assert success["exit_code"] == 0
    assert "agentforge plan .tmp/builder-runs/<run-id>/domain-pack.yaml" in success["commands"]
    assert failure["ok"] is False
    assert failure["status"] == "error"
    assert failure["errors"]


def test_generate_local_app_writes_only_under_builder_runs(tmp_path):
    result = local_run.generate_local_app(_coach_blueprint(), repo_root=tmp_path)

    assert result["ok"] is True
    assert result["run_id"].startswith("run-")
    root = tmp_path / ".tmp" / "builder-runs"
    paths = local_run.safe_run_paths(result["run_id"], repo_root=tmp_path)
    assert paths.blueprint_path.exists()
    assert paths.app_dir.exists()
    assert (paths.app_dir / "Makefile").exists()
    assert paths.run_dir.resolve().is_relative_to(root.resolve())
    assert not (tmp_path / "examples").exists()
    assert result["generated_path"].startswith(".tmp/builder-runs/")
    assert result["commands"] == [
        f"agentforge generate .tmp/builder-runs/{result['run_id']}/domain-pack.yaml --output .tmp/builder-runs/{result['run_id']}/app"
    ]


def test_generate_local_app_reports_validation_failure(tmp_path):
    result = local_run.generate_local_app({"name": "bad"}, repo_root=tmp_path)

    assert result["ok"] is False
    assert result["step"] == "generate"
    assert not (tmp_path / ".tmp" / "builder-runs").exists()


def test_validate_generated_app_success_and_failure(tmp_path, monkeypatch):
    paths = local_run.safe_run_paths("run-abc12345", repo_root=tmp_path)
    paths.app_dir.mkdir(parents=True)
    (paths.app_dir / "Makefile").write_text("validate:\n\t@echo ok\n", encoding="utf-8")
    monkeypatch.setattr(local_run, "_run_allowlisted_command", lambda command, cwd, timeout_seconds: {
        "exit_code": 0,
        "stdout": "ok",
        "stderr": "",
        "truncated": False,
    })

    success = local_run.validate_generated_app("run-abc12345", repo_root=tmp_path)
    missing = local_run.validate_generated_app("run-missing1", repo_root=tmp_path)

    assert success["ok"] is True
    assert success["commands"] == ["cd .tmp/builder-runs/run-abc12345/app", "make validate"]
    assert success["stdout"] == "ok"
    assert missing["ok"] is False
    assert "does not exist" in missing["stderr"]


def test_validate_generated_app_failure_from_make(tmp_path, monkeypatch):
    paths = local_run.safe_run_paths("run-fail123", repo_root=tmp_path)
    paths.app_dir.mkdir(parents=True)
    (paths.app_dir / "Makefile").write_text("validate:\n\texit 1\n", encoding="utf-8")
    monkeypatch.setattr(local_run, "_run_allowlisted_command", lambda command, cwd, timeout_seconds: {
        "exit_code": 2,
        "stdout": "",
        "stderr": "failed",
        "truncated": False,
    })

    result = local_run.validate_generated_app("run-fail123", repo_root=tmp_path)

    assert result["ok"] is False
    assert result["exit_code"] == 2
    assert result["errors"] == ["make validate failed"]


def test_allowlisted_command_rejects_arbitrary_shell(tmp_path):
    with pytest.raises(ValueError):
        local_run._run_allowlisted_command(["python", "-c", "print(1)"], cwd=tmp_path, timeout_seconds=1)
    with pytest.raises(ValueError):
        local_run._popen_allowlisted_service(["python", "-m", "http.server"], cwd=tmp_path)


def test_start_backend_frontend_lifecycle_with_mocked_processes(tmp_path, monkeypatch):
    paths = local_run.safe_run_paths("run-servers1", repo_root=tmp_path)
    paths.app_dir.mkdir(parents=True)
    (paths.app_dir / "Makefile").write_text("run-backend:\n\t@echo backend\nrun-frontend:\n\t@echo frontend\n", encoding="utf-8")
    created = []

    def fake_popen(command, cwd):
        proc = FakeProc(pid=5000 + len(created), stdout=f"started {' '.join(command)}\n")
        created.append((command, cwd, proc))
        return proc

    monkeypatch.setattr(local_run, "_popen_allowlisted_service", fake_popen)
    monkeypatch.setattr(local_run, "_url_available", lambda url, timeout: True)
    monkeypatch.setattr(local_run, "_tcp_port_available", lambda host, port: True)
    monkeypatch.setattr(local_run, "_listening_pids", lambda port: set())
    monkeypatch.setattr(local_run, "_frontend_render_check", lambda app_dir, url, timeout: (True, ""))

    backend = local_run.start_generated_app_service("run-servers1", "backend", repo_root=tmp_path)
    frontend = local_run.start_generated_app_service("run-servers1", "frontend", repo_root=tmp_path)

    assert backend["ok"] is True
    assert backend["status"] == "running"
    assert backend["url"] == "http://127.0.0.1:8000/docs"
    assert backend["health_url"] == "http://127.0.0.1:8000/health"
    assert backend["commands"] == ["cd .tmp/builder-runs/run-servers1/app", "make run-backend"]
    assert frontend["status"] == "running"
    assert frontend["url"] == "http://localhost:5173"
    assert created[0][0] == ["make", "run-backend"]
    assert created[1][0] == ["make", "run-frontend"]


def test_duplicate_start_returns_existing_status_without_new_process(tmp_path, monkeypatch):
    paths = local_run.safe_run_paths("run-dupe123", repo_root=tmp_path)
    paths.app_dir.mkdir(parents=True)
    (paths.app_dir / "Makefile").write_text("run-backend:\n\t@echo backend\n", encoding="utf-8")
    calls = []

    def fake_popen(command, cwd):
        calls.append(command)
        return FakeProc(pid=6001)

    monkeypatch.setattr(local_run, "_popen_allowlisted_service", fake_popen)
    monkeypatch.setattr(local_run, "_url_available", lambda url, timeout: True)
    monkeypatch.setattr(local_run, "_tcp_port_available", lambda host, port: True)
    monkeypatch.setattr(local_run, "_listening_pids", lambda port: set())

    first = local_run.start_generated_app_service("run-dupe123", "backend", repo_root=tmp_path)
    second = local_run.start_generated_app_service("run-dupe123", "backend", repo_root=tmp_path)

    assert first["status"] == "running"
    assert second["status"] == "running"
    assert second["duplicate"] is True
    assert len(calls) == 1


def test_stop_frontend_cleans_builder_vite_child_on_fixed_port(tmp_path, monkeypatch):
    paths = local_run.safe_run_paths("run-child11", repo_root=tmp_path)
    paths.app_dir.mkdir(parents=True)
    (paths.app_dir / "Makefile").write_text("run-frontend:\n\t@echo frontend\n", encoding="utf-8")
    terminated = []
    monkeypatch.setattr(local_run, "_tcp_port_available", lambda host, port: True)
    monkeypatch.setattr(local_run, "_popen_allowlisted_service", lambda command, cwd: FakeProc(pid=7100))
    monkeypatch.setattr(local_run, "_url_available", lambda url, timeout: True)
    monkeypatch.setattr(local_run, "_frontend_render_check", lambda app_dir, url, timeout: (True, ""))
    listening = iter([set(), {7200}])
    monkeypatch.setattr(local_run, "_listening_pids", lambda port: next(listening))
    monkeypatch.setattr(local_run, "_is_builder_run_process", lambda pid: True)
    monkeypatch.setattr(local_run, "_terminate_pid_tree", lambda pid: terminated.append(pid))

    local_run.start_generated_app_service("run-child11", "frontend", repo_root=tmp_path)
    result = local_run.stop_generated_app_service("run-child11", "frontend", repo_root=tmp_path)

    assert result["status"] == "stopped"
    assert terminated == [7200]


def test_starting_new_run_stops_previous_builder_started_service(tmp_path, monkeypatch):
    for run_id in ("run-stop111", "run-stop222"):
        paths = local_run.safe_run_paths(run_id, repo_root=tmp_path)
        paths.app_dir.mkdir(parents=True)
        (paths.app_dir / "Makefile").write_text("run-backend:\n\t@echo backend\n", encoding="utf-8")
    procs = []
    stopped = []

    def fake_popen(command, cwd):
        proc = FakeProc(pid=7000 + len(procs))
        procs.append(proc)
        return proc

    monkeypatch.setattr(local_run, "_popen_allowlisted_service", fake_popen)
    monkeypatch.setattr(local_run, "_url_available", lambda url, timeout: True)
    monkeypatch.setattr(local_run, "_tcp_port_available", lambda host, port: True)
    monkeypatch.setattr(local_run, "_listening_pids", lambda port: set())
    monkeypatch.setattr(local_run, "_terminate_process_tree", lambda proc: (stopped.append(proc.pid), setattr(proc, "returncode", -15)))

    first = local_run.start_generated_app_service("run-stop111", "backend", repo_root=tmp_path)
    second = local_run.start_generated_app_service("run-stop222", "backend", repo_root=tmp_path)

    assert first["status"] == "running"
    assert second["status"] == "running"
    assert stopped == [7000]
    assert local_run.get_generated_app_service_status("run-stop111", "backend", repo_root=tmp_path)["status"] == "stopped"
    assert local_run.get_generated_app_service_status("run-stop222", "backend", repo_root=tmp_path)["status"] == "running"


def test_backend_port_occupied_returns_clear_failure(tmp_path, monkeypatch):
    paths = local_run.safe_run_paths("run-backport", repo_root=tmp_path)
    paths.app_dir.mkdir(parents=True)
    (paths.app_dir / "Makefile").write_text("run-backend:\n\t@echo backend\n", encoding="utf-8")
    monkeypatch.setattr(local_run, "_tcp_port_available", lambda host, port: False)
    monkeypatch.setattr(local_run, "_listening_pids", lambda port: {12345})

    result = local_run.start_generated_app_service("run-backport", "backend", repo_root=tmp_path)

    assert result["ok"] is False
    assert result["status"] == "error"
    assert "Backend port 8000 is already in use by another process" in result["stderr"]


def test_frontend_port_occupied_by_non_builder_process_returns_clear_failure(tmp_path, monkeypatch):
    paths = local_run.safe_run_paths("run-port123", repo_root=tmp_path)
    paths.app_dir.mkdir(parents=True)
    (paths.app_dir / "Makefile").write_text("run-frontend:\n\t@echo frontend\n", encoding="utf-8")
    monkeypatch.setattr(local_run, "_tcp_port_available", lambda host, port: False)
    monkeypatch.setattr(local_run, "_listening_pids", lambda port: {12345})
    monkeypatch.setattr(local_run, "_is_builder_run_process", lambda pid: False)

    result = local_run.start_generated_app_service("run-port123", "frontend", repo_root=tmp_path)

    assert result["ok"] is False
    assert result["status"] == "error"
    assert "Frontend port 5173 is already in use by another process" in result["stderr"]


def test_frontend_port_held_by_orphan_builder_process_is_reclaimed(tmp_path, monkeypatch):
    paths = local_run.safe_run_paths("run-reclaim1", repo_root=tmp_path)
    paths.app_dir.mkdir(parents=True)
    (paths.app_dir / "Makefile").write_text("run-frontend:\n\t@echo frontend\n", encoding="utf-8")
    availability = iter([False, True, True, True])
    terminated = []
    monkeypatch.setattr(local_run, "_tcp_port_available", lambda host, port: next(availability))
    monkeypatch.setattr(local_run, "_listening_pids", lambda port: {4496})
    monkeypatch.setattr(local_run, "_is_builder_run_process", lambda pid: True)
    monkeypatch.setattr(local_run, "_terminate_pid_tree", lambda pid: terminated.append(pid))
    monkeypatch.setattr(local_run, "_popen_allowlisted_service", lambda command, cwd: FakeProc(pid=6201))
    monkeypatch.setattr(local_run, "_url_available", lambda url, timeout: True)
    monkeypatch.setattr(local_run, "_frontend_render_check", lambda app_dir, url, timeout: (True, ""))

    result = local_run.start_generated_app_service("run-reclaim1", "frontend", repo_root=tmp_path)

    assert result["status"] == "running"
    assert terminated == [4496]


def test_backend_port_held_by_orphan_builder_process_is_reclaimed(tmp_path, monkeypatch):
    paths = local_run.safe_run_paths("run-backreclaim1", repo_root=tmp_path)
    paths.app_dir.mkdir(parents=True)
    (paths.app_dir / "Makefile").write_text("run-backend:\n\t@echo backend\n", encoding="utf-8")
    terminated = []
    monkeypatch.setattr(local_run, "_tcp_port_available", lambda host, port: True)
    monkeypatch.setattr(local_run, "_listening_pids", lambda port: {4497})
    monkeypatch.setattr(local_run, "_is_builder_run_process", lambda pid: True)
    monkeypatch.setattr(local_run, "_terminate_pid_tree", lambda pid: terminated.append(pid))
    monkeypatch.setattr(local_run, "_popen_allowlisted_service", lambda command, cwd: FakeProc(pid=6202))
    monkeypatch.setattr(local_run, "_url_available", lambda url, timeout: True)

    result = local_run.start_generated_app_service("run-backreclaim1", "backend", repo_root=tmp_path)

    assert result["status"] == "running"
    assert terminated == [4497]


def test_backend_port_held_by_generated_backend_child_is_reclaimed(tmp_path, monkeypatch):
    paths = local_run.safe_run_paths("run-backchild1", repo_root=tmp_path)
    paths.app_dir.mkdir(parents=True)
    (paths.app_dir / "Makefile").write_text("run-backend:\n\t@echo backend\n", encoding="utf-8")
    terminated = []
    monkeypatch.setattr(local_run, "_tcp_port_available", lambda host, port: True)
    monkeypatch.setattr(local_run, "_listening_pids", lambda port: {4498})
    monkeypatch.setattr(local_run, "_is_builder_run_process", lambda pid: False)
    monkeypatch.setattr(local_run, "_is_generated_backend_listener", lambda pid, spec: True)
    monkeypatch.setattr(local_run, "_terminate_pid_tree", lambda pid: terminated.append(pid))
    monkeypatch.setattr(local_run, "_popen_allowlisted_service", lambda command, cwd: FakeProc(pid=6203))
    monkeypatch.setattr(local_run, "_url_available", lambda url, timeout: True)

    result = local_run.start_generated_app_service("run-backchild1", "backend", repo_root=tmp_path)

    assert result["status"] == "running"
    assert terminated == [4498]


def test_backend_port_reported_as_dead_reloader_reclaims_generated_child(tmp_path, monkeypatch):
    paths = local_run.safe_run_paths("run-backchild2", repo_root=tmp_path)
    paths.app_dir.mkdir(parents=True)
    (paths.app_dir / "Makefile").write_text("run-backend:\n\t@echo backend\n", encoding="utf-8")
    terminated = []
    monkeypatch.setattr(local_run, "_tcp_port_available", lambda host, port: True)
    monkeypatch.setattr(local_run, "_listening_pids", lambda port: {3652})
    monkeypatch.setattr(local_run, "_child_pids", lambda pid: [17688])
    monkeypatch.setattr(local_run, "_is_builder_run_process", lambda pid: False)
    monkeypatch.setattr(local_run, "_is_generated_backend_listener", lambda pid, spec: pid == 17688)
    monkeypatch.setattr(local_run, "_terminate_pid_tree", lambda pid: terminated.append(pid))
    monkeypatch.setattr(local_run, "_popen_allowlisted_service", lambda command, cwd: FakeProc(pid=6204))
    monkeypatch.setattr(local_run, "_url_available", lambda url, timeout: True)

    result = local_run.start_generated_app_service("run-backchild2", "backend", repo_root=tmp_path)

    assert result["status"] == "running"
    assert terminated == [17688]


def test_reset_generated_app_services_stops_registered_processes_and_reclaims_ports(tmp_path, monkeypatch):
    paths = local_run.safe_run_paths("run-reset11", repo_root=tmp_path)
    paths.app_dir.mkdir(parents=True)
    proc = FakeProc(pid=8100)
    local_run._PROCESS_REGISTRY[local_run._process_key(paths, "backend")] = local_run.ManagedProcess(
        run_id=paths.run_id,
        service="backend",
        command=["make", "run-backend"],
        cwd=paths.app_dir,
        url="http://127.0.0.1:8000/docs",
        proc=proc,
    )
    stopped = []
    terminated = []
    monkeypatch.setattr(local_run, "_terminate_process_tree", lambda target: (stopped.append(target.pid), setattr(target, "returncode", -15)))
    monkeypatch.setattr(local_run, "_listening_pids", lambda port: {8200 + port})
    monkeypatch.setattr(local_run, "_is_builder_run_process", lambda pid: True)
    monkeypatch.setattr(local_run, "_terminate_pid_tree", lambda pid: terminated.append(pid))

    result = local_run.reset_generated_app_services(repo_root=tmp_path)

    assert result["ok"] is True
    assert result["status"] == "stopped"
    assert result["stopped"] == [{"run_id": "run-reset11", "service": "backend", "pid": 8100}]
    assert result["reclaimed_pids"] == [13373, 16200]
    assert stopped == [8100]
    assert sorted(terminated) == [13373, 16200]
    assert local_run._process_key(paths, "backend") not in local_run._PROCESS_REGISTRY


def test_frontend_process_exit_before_health_check_reports_failed(tmp_path, monkeypatch):
    paths = local_run.safe_run_paths("run-exit123", repo_root=tmp_path)
    paths.app_dir.mkdir(parents=True)
    (paths.app_dir / "Makefile").write_text("run-frontend:\n\t@echo frontend\n", encoding="utf-8")
    proc = FakeProc(pid=6200)
    proc.returncode = 2
    monkeypatch.setattr(local_run, "_tcp_port_available", lambda host, port: True)
    monkeypatch.setattr(local_run, "_popen_allowlisted_service", lambda command, cwd: proc)

    result = local_run.start_generated_app_service("run-exit123", "frontend", repo_root=tmp_path)

    assert result["ok"] is False
    assert result["status"] == "failed"
    assert result["errors"] == ["frontend process exited"]


def test_frontend_render_check_catches_blank_wrong_and_current_app(tmp_path, monkeypatch):
    paths = local_run.safe_run_paths("run-render1", repo_root=tmp_path)
    frontend_dir = paths.app_dir / "frontend"
    frontend_dir.mkdir(parents=True)
    (frontend_dir / "index.html").write_text('<title>Current Tennis Coach App</title><div id="root"></div>', encoding="utf-8")

    assert local_run._frontend_render_check(paths.app_dir, "mock://current", timeout=1)[0] is False

    responses = {
        "http://blank": ("", ""),
        "http://wrong": ('<title>Old Vendor App</title><div id="root"></div>', ""),
        "http://current": ('<title>Current Tennis Coach App</title><div id="root"></div><script type="module"></script>', ""),
    }

    def fake_fetch(url, timeout):
        return responses[url]

    monkeypatch.setattr(local_run, "_fetch_text", fake_fetch)
    blank = local_run._frontend_render_check(paths.app_dir, "http://blank", timeout=1)
    wrong = local_run._frontend_render_check(paths.app_dir, "http://wrong", timeout=1)
    current = local_run._frontend_render_check(paths.app_dir, "http://current", timeout=1)

    assert blank == (False, "frontend render check failed: blank response")
    assert wrong[0] is False
    assert "Current Tennis Coach App" in wrong[1]
    assert current == (True, "")


def test_start_service_reports_starting_until_health_url_is_reachable(tmp_path, monkeypatch):
    paths = local_run.safe_run_paths("run-starting", repo_root=tmp_path)
    paths.app_dir.mkdir(parents=True)
    (paths.app_dir / "Makefile").write_text("run-backend:\n\t@echo backend\n", encoding="utf-8")
    monkeypatch.setattr(local_run, "_popen_allowlisted_service", lambda command, cwd: FakeProc(pid=6100))
    monkeypatch.setattr(local_run, "_wait_for_service_ready", lambda managed, spec: False)
    monkeypatch.setattr(local_run, "_url_available", lambda url, timeout: False)
    monkeypatch.setattr(local_run, "_tcp_port_available", lambda host, port: True)
    monkeypatch.setattr(local_run, "_listening_pids", lambda port: set())

    result = local_run.start_generated_app_service("run-starting", "backend", repo_root=tmp_path)

    assert result["ok"] is True
    assert result["status"] == "starting"
    assert result["url"] == "http://127.0.0.1:8000/docs"
    assert result["health_url"] == "http://127.0.0.1:8000/health"


def test_start_service_requires_generated_app_and_makefile_target(tmp_path):
    missing_app = local_run.start_generated_app_service("run-missing2", "backend", repo_root=tmp_path)
    paths = local_run.safe_run_paths("run-notarget", repo_root=tmp_path)
    paths.app_dir.mkdir(parents=True)
    (paths.app_dir / "Makefile").write_text("validate:\n\t@echo ok\n", encoding="utf-8")
    missing_target = local_run.start_generated_app_service("run-notarget", "frontend", repo_root=tmp_path)

    assert missing_app["ok"] is False
    assert "does not exist" in missing_app["stderr"]
    assert missing_target["ok"] is False
    assert "no run-frontend target" in missing_target["stderr"]


def test_backend_service_overrides_repo_database_url_for_local_sqlite(tmp_path, monkeypatch):
    captured = {}

    class DummyPopen(FakeProc):
        def __init__(self, *args, **kwargs):
            captured.update(kwargs)
            super().__init__()

    monkeypatch.setattr(local_run.subprocess, "Popen", DummyPopen)
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://example")

    local_run._popen_allowlisted_service(["make", "run-backend"], cwd=tmp_path)

    assert captured["env"]["DATABASE_URL"] == "sqlite:///./app.db"


def test_safe_subprocess_env_keeps_tool_paths_but_excludes_secrets(monkeypatch):
    monkeypatch.setenv("APPDATA", "tool-cache")
    monkeypatch.setenv("SYSTEMROOT", "windows-root")
    monkeypatch.setenv("OPENAI_API_KEY", "secret")
    monkeypatch.setenv("GITHUB_TOKEN", "secret")
    monkeypatch.setenv("BASIC_AUTH", "secret")

    env = local_run._safe_subprocess_env()

    assert env["APPDATA"] == "tool-cache"
    assert env["SYSTEMROOT"] == "windows-root"
    assert "OPENAI_API_KEY" not in env
    assert "GITHUB_TOKEN" not in env
    assert "BASIC_AUTH" not in env


def test_timeout_and_log_truncation(monkeypatch, tmp_path):
    def fake_run(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd=["make", "validate"], timeout=1, output="x" * 13000, stderr="secret?" * 3000)

    monkeypatch.setattr(local_run.subprocess, "run", fake_run)
    result = local_run._run_allowlisted_command(["make", "validate"], cwd=tmp_path, timeout_seconds=1)

    assert result["exit_code"] == 124
    assert result["timed_out"] is True
    assert result["truncated"] is True
    assert len(result["stdout"]) <= 12050
    assert "timed out" in result["stderr"]


def test_server_local_run_endpoints_round_trip(tmp_path, monkeypatch):
    monkeypatch.setattr(local_run, "_run_allowlisted_command", lambda command, cwd, timeout_seconds: {
        "exit_code": 0,
        "stdout": "validation ok",
        "stderr": "",
        "truncated": False,
    })
    monkeypatch.setattr(planner_server, "generate_local_app", lambda blueprint: local_run.generate_local_app(blueprint, repo_root=tmp_path))
    monkeypatch.setattr(planner_server, "validate_generated_app", lambda run_id: local_run.validate_generated_app(run_id, repo_root=tmp_path))
    monkeypatch.setattr(planner_server, "start_generated_app_service", lambda run_id, service: {"ok": True, "step": "start-service", "status": "running", "service": service, "run_id": run_id, "url": "http://127.0.0.1:8000", "commands": ["make run-backend"], "stdout": "", "stderr": "", "errors": []})
    monkeypatch.setattr(planner_server, "stop_generated_app_service", lambda run_id, service: {"ok": True, "step": "stop-service", "status": "stopped", "service": service, "run_id": run_id, "url": "http://127.0.0.1:8000", "commands": ["make run-backend"], "stdout": "", "stderr": "", "errors": []})
    monkeypatch.setattr(planner_server, "reset_generated_app_services", lambda: {"ok": True, "step": "reset-session", "status": "stopped", "stopped": [], "reclaimed_pids": [], "errors": []})
    server = PlannerServer(("127.0.0.1", 0), tmp_path)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_port}"
    try:
        blueprint = _coach_blueprint()
        valid = _post_json(base + "/api/planner/local-run/validate-blueprint", {"blueprint": blueprint})
        generated = _post_json(base + "/api/planner/local-run/generate", {"blueprint": blueprint})
        checked = _post_json(base + "/api/planner/local-run/validate-app", {"run_id": generated["run_id"]})
        started = _post_json(base + "/api/planner/local-run/start-service", {"run_id": generated["run_id"], "service": "backend"})
        stopped = _post_json(base + "/api/planner/local-run/stop-service", {"run_id": generated["run_id"], "service": "backend"})
        reset = _post_json(base + "/api/planner/local-run/reset-session", {})
        traversal = _post_json(base + "/api/planner/local-run/validate-app", {"run_id": "../escape"}, expect_status=400)

        assert valid["ok"] is True
        assert generated["ok"] is True
        assert checked["ok"] is True
        assert started["status"] == "running"
        assert stopped["status"] == "stopped"
        assert reset["status"] == "stopped"
        assert "invalid local run id" in json.dumps(traversal)
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


class FakeProc:
    def __init__(self, pid=1234, stdout="", stderr=""):
        self.pid = pid
        self.returncode = None
        self.stdout = io.StringIO(stdout)
        self.stderr = io.StringIO(stderr)

    def poll(self):
        return self.returncode

    def wait(self, timeout=None):
        self.returncode = 0 if self.returncode is None else self.returncode
        return self.returncode

    def kill(self):
        self.returncode = -9


def _post_json(url, payload, expect_status=200):
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            assert response.status == expect_status
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        assert exc.code == expect_status
        return json.loads(exc.read().decode("utf-8"))

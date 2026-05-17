"""Tests for local .env loading in agentforge serve-builder."""
import json
import os
import sys
import threading
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "generator"))

import agentforge.planner.server as planner_server
from agentforge.planner.server import create_builder_server, load_builder_dotenv


def test_load_builder_dotenv_loads_simple_values_and_strips_quotes(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "AGENTFORGE_ASSISTANT_PROVIDER=openai\n"
        "OPENAI_API_KEY=\"secret-key\"\n"
        "AGENTFORGE_ASSISTANT_LLM_MODEL='gpt-test'\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(planner_server, "_env_file_is_git_ignored", lambda _path: True)
    env = {}

    result = load_builder_dotenv(env_file, environ=env)

    assert result.existed is True
    assert set(result.loaded_keys) == {"AGENTFORGE_ASSISTANT_PROVIDER", "OPENAI_API_KEY", "AGENTFORGE_ASSISTANT_LLM_MODEL"}
    assert env["AGENTFORGE_ASSISTANT_PROVIDER"] == "openai"
    assert env["OPENAI_API_KEY"] == "secret-key"
    assert env["AGENTFORGE_ASSISTANT_LLM_MODEL"] == "gpt-test"


def test_load_builder_dotenv_does_not_override_existing_env(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text("OPENAI_API_KEY=from-file\nNEW_VALUE=loaded\n", encoding="utf-8")
    monkeypatch.setattr(planner_server, "_env_file_is_git_ignored", lambda _path: True)
    env = {"OPENAI_API_KEY": "from-shell"}

    result = load_builder_dotenv(env_file, environ=env)

    assert env["OPENAI_API_KEY"] == "from-shell"
    assert env["NEW_VALUE"] == "loaded"
    assert result.skipped_existing_keys == ["OPENAI_API_KEY"]


def test_load_builder_dotenv_ignores_comments_blank_lines_and_malformed(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "# comment\n\n"
        "GOOD=value\n"
        "not valid\n"
        "BAD-KEY=value\n"
        "ALSO_GOOD=two=parts\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(planner_server, "_env_file_is_git_ignored", lambda _path: True)
    env = {}

    result = load_builder_dotenv(env_file, environ=env)

    assert env == {"GOOD": "value", "ALSO_GOOD": "two=parts"}
    assert result.malformed_lines == 2


def test_load_builder_dotenv_missing_file_is_noop(tmp_path):
    env = {}

    result = load_builder_dotenv(tmp_path / ".env", environ=env)

    assert result.existed is False
    assert env == {}
    assert result.loaded_keys == []


def test_env_warning_contains_no_secret_values(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text("OPENAI_API_KEY=super-secret-value\n", encoding="utf-8")
    monkeypatch.setattr(planner_server, "_env_file_is_git_ignored", lambda _path: False)

    result = load_builder_dotenv(env_file, environ={})

    assert result.warning
    assert "super-secret-value" not in result.warning
    assert "OPENAI_API_KEY" not in result.warning
    assert ".env" in result.warning


def test_create_builder_server_loads_dotenv_before_assistant_from_env(tmp_path, monkeypatch):
    (tmp_path / ".env").write_text(
        "AGENTFORGE_ASSISTANT_PROVIDER=openai\nOPENAI_API_KEY=test-key\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("AGENTFORGE_ASSISTANT_PROVIDER", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr(planner_server, "_env_file_is_git_ignored", lambda _path: True)

    server, env_result = create_builder_server("127.0.0.1", 0, tmp_path)
    try:
        assert env_result is not None and env_result.existed is True
        assert server.assistant.live_provider_enabled is True
        assert server.assistant.mode == "live"
    finally:
        server.server_close()


def test_status_endpoint_does_not_expose_loaded_env_values(tmp_path, monkeypatch):
    (tmp_path / ".env").write_text(
        "AGENTFORGE_ASSISTANT_PROVIDER=openai\nOPENAI_API_KEY=status-secret\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("AGENTFORGE_ASSISTANT_PROVIDER", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr(planner_server, "_env_file_is_git_ignored", lambda _path: True)
    server, _env_result = create_builder_server("127.0.0.1", 0, tmp_path)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{server.server_port}/api/planner/status", timeout=5) as response:
            body = response.read().decode("utf-8")
        parsed = json.loads(body)
        assert parsed == {"mode": "live", "planner_available": True, "live_provider": True}
        assert "status-secret" not in body
        assert "OPENAI_API_KEY" not in body
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_normal_builder_server_does_not_require_dotenv(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("AGENTFORGE_ASSISTANT_PROVIDER", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    server, env_result = create_builder_server("127.0.0.1", 0, tmp_path)
    try:
        assert env_result is not None and env_result.existed is False
        assert server.assistant.mode == "scripted"
        assert server.assistant.live_provider_enabled is False
    finally:
        server.server_close()

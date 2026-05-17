"""Browser regression smoke for the Builder Assistant Apply flow.

This covers the real click path that static HTML/JS tests cannot: submit an
assistant prompt, wait for a proposal, click Apply and review plan, and confirm
Review + Live App Plan use the assistant-applied model-driven Blueprint.
"""
from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path
from urllib.request import urlopen

import pytest


ROOT = Path(__file__).resolve().parents[2]
TMP_DIR = ROOT / ".tmp"
PLAYWRIGHT_DIR = TMP_DIR / "node_modules" / "playwright"


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _wait_for_status(port: int) -> None:
    deadline = time.time() + 20
    last_error: Exception | None = None
    while time.time() < deadline:
        try:
            with urlopen(f"http://127.0.0.1:{port}/api/planner/status", timeout=1) as response:
                if response.status == 200:
                    return
        except Exception as exc:  # pragma: no cover - diagnostic path
            last_error = exc
            time.sleep(0.2)
    raise AssertionError(f"builder server did not start: {last_error}")


@pytest.mark.skipif(not PLAYWRIGHT_DIR.exists(), reason="Playwright browser smoke requires .tmp/node_modules/playwright")
def test_assistant_apply_updates_review_and_live_plan_in_browser(tmp_path):
    port = _free_port()
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "generator")
    # Browser regression must not depend on live network/API keys.
    env["AGENTFORGE_ASSISTANT_PROVIDER"] = "scripted"
    env.pop("OPENAI_API_KEY", None)
    server = subprocess.Popen(
        [sys.executable, "-m", "agentforge.cli", "serve-builder", "--host", "127.0.0.1", "--port", str(port)],
        cwd=ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    try:
        _wait_for_status(port)
        script = tmp_path / "assistant-apply-smoke.mjs"
        playwright_import = (PLAYWRIGHT_DIR / "index.mjs").resolve().as_uri()
        script.write_text(
            """
import { chromium } from '__PLAYWRIGHT_IMPORT__';
const port = process.argv[2];
const browser = await chromium.launch({ headless: true });
const page = await browser.newPage();
const consoleErrors = [];
const failedRequests = [];
page.on('console', msg => { if (msg.type() === 'error') consoleErrors.push(msg.text()); });
page.on('requestfailed', req => failedRequests.push(`${req.method()} ${req.url()} ${req.failure()?.errorText}`));
try {
  await page.goto(`http://127.0.0.1:${port}/`, { waitUntil: 'networkidle' });
  await page.click('[data-step-target="new-app"]');
  await page.fill('#assistant-input', 'support ticket triage with title status priority owner notes to close tickets');
  await page.click('#assistant-send');
  await page.waitForSelector('#assistant-proposal:not(.hidden)', { timeout: 30000 });
  const proposalDisabled = await page.locator('#assistant-apply').isDisabled();
  await page.click('#assistant-apply');
  await page.waitForSelector('#review-flow.active', { timeout: 10000 });
  const activeStep = await page.locator('.wizard-step.active').getAttribute('data-step');
  const livePlan = await page.locator('.live-plan').innerText();
  const review = await page.locator('#review-flow').innerText();
  const classicDraftClicks = await page.locator('#draft-blueprint').evaluate(el => el.dataset.clicked || '0').catch(() => '0');
  console.log(JSON.stringify({ proposalDisabled, activeStep, livePlan, review, classicDraftClicks, consoleErrors, failedRequests }));
} finally {
  await browser.close();
}
""".replace("__PLAYWRIGHT_IMPORT__", playwright_import),
            encoding="utf-8",
        )
        result = subprocess.run(
            ["node", str(script), str(port)],
            cwd=TMP_DIR,
            text=True,
            capture_output=True,
            timeout=60,
        )
        assert result.returncode == 0, result.stdout + result.stderr
        payload = json.loads(result.stdout.strip().splitlines()[-1])
        assert payload["proposalDisabled"] is False
        assert payload["activeStep"] == "review"
        live_plan = payload["livePlan"].lower()
        review = payload["review"].lower()
        assert "model-driven" in live_plan
        assert "tickets" in live_plan or "ticket" in live_plan
        assert "ingestion scoring" not in live_plan
        assert "notification triage" not in live_plan
        assert "model-driven app summary" in review
        assert "tickets" in review or "ticket" in review
        assert "scoring / triage labels" not in review
        assert payload["classicDraftClicks"] == "0"
        assert payload["consoleErrors"] == []
        assert payload["failedRequests"] == []
    finally:
        server.terminate()
        try:
            server.wait(timeout=5)
        except subprocess.TimeoutExpired:  # pragma: no cover - cleanup path
            server.kill()

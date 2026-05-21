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
  const visibleOnStart = await page.locator('#assistant-panel').isVisible();
  const startStep = await page.locator('.wizard-step.active').getAttribute('data-step');
  const initialCanvasState = await page.locator('#builder-shell').getAttribute('data-canvas-state');
  const thinkingVisibleOnStart = await page.locator('#canvas-thinking-overlay').isVisible();
  const inlineThinkingVisibleOnStart = await page.locator('#hero-composer-thinking').isVisible();
  await page.fill('#hero-composer-input', 'support ticket triage with title status priority owner notes to close tickets');
  await page.click('#hero-composer-send');
  await page.waitForSelector('#assistant-proposal:not(.hidden)', { timeout: 30000 });
  const visibleOnDescribe = await page.locator('#assistant-panel').isVisible();
  const planReadyCanvasState = await page.locator('#builder-shell').getAttribute('data-canvas-state');
  const thinkingVisibleOnProposal = await page.locator('#canvas-thinking-overlay').isVisible();
  const proposalBox = await page.locator('#assistant-proposal').boundingBox();
  const applyBox = await page.locator('#assistant-apply').boundingBox();
  const proposalChangesCollapsed = await page.locator('.assistant-proposal-changes').evaluate(el => !el.open).catch(() => true);
  const proposalInMainCanvas = await page.locator('#new-app-flow #assistant-proposal').isVisible();
  const proposalInRail = await page.locator('.builder-side-panel #assistant-proposal').count();
  const proposalText = await page.locator('#assistant-proposal').innerText();
  const proposalDisabled = await page.locator('#assistant-apply').isDisabled();
  await page.click('#assistant-apply');
  await page.waitForSelector('#review-flow.active', { timeout: 10000 });
  const activeStep = await page.locator('.wizard-step.active').getAttribute('data-step');
  const appliedCanvasState = await page.locator('#builder-shell').getAttribute('data-canvas-state');
  const visibleOnReview = await page.locator('#assistant-panel').isVisible();
  const thinkingVisibleOnReview = await page.locator('#canvas-thinking-overlay').isVisible();
  const historyCollapsedAfterApply = await page.locator('#assistant-history').evaluate(el => !el.open);
  await page.locator('#assistant-history').evaluate(el => { el.open = true; });
  const historyScrollStyle = await page.locator('#assistant-history #assistant-log').evaluate(el => getComputedStyle(el).overflowY);
  const historyMaxHeight = await page.locator('#assistant-history #assistant-log').evaluate(el => getComputedStyle(el).maxHeight);
  const localRunReachable = await page.locator('#local-run-panel').isVisible();
  const localRunValidateEnabled = await page.locator('#local-run-validate-blueprint').isEnabled();
  await page.click('[data-step-target="generate"]');
  await page.waitForSelector('#generate-flow.active', { timeout: 10000 });
  const exportStep = await page.locator('.wizard-step.active').getAttribute('data-step');
  const visibleOnExport = await page.locator('#assistant-panel').isVisible();
  const thinkingVisibleOnExport = await page.locator('#canvas-thinking-overlay').isVisible();
  const advancedVisible = await page.locator('.export-advanced-drawer').isVisible();
  await page.locator('.export-advanced-drawer').evaluate(el => { el.open = true; });
  const cliStillVisible = await page.locator('.command-card').isVisible();
  const livePlan = await page.locator('.live-plan').innerText();
  const review = await page.locator('#review-flow').innerText();
  const classicDraftClicks = await page.locator('#draft-blueprint').evaluate(el => el.dataset.clicked || '0').catch(() => '0');
  console.log(JSON.stringify({ visibleOnStart, startStep, initialCanvasState, thinkingVisibleOnStart, inlineThinkingVisibleOnStart, visibleOnDescribe, planReadyCanvasState, thinkingVisibleOnProposal, proposalBox, applyBox, proposalChangesCollapsed, proposalInMainCanvas, proposalInRail, proposalText, proposalDisabled, activeStep, appliedCanvasState, visibleOnReview, thinkingVisibleOnReview, historyCollapsedAfterApply, historyScrollStyle, historyMaxHeight, localRunReachable, localRunValidateEnabled, exportStep, visibleOnExport, thinkingVisibleOnExport, advancedVisible, cliStillVisible, livePlan, review, classicDraftClicks, consoleErrors, failedRequests }));
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
        assert payload["visibleOnStart"] is True
        assert payload["startStep"] == "start"
        assert payload["initialCanvasState"] == "empty"
        assert payload["thinkingVisibleOnStart"] is False
        assert payload["inlineThinkingVisibleOnStart"] is False
        assert payload["visibleOnDescribe"] is True
        assert payload["planReadyCanvasState"] == "plan-ready"
        assert payload["thinkingVisibleOnProposal"] is False
        assert payload["proposalInMainCanvas"] is True
        assert payload["proposalInRail"] == 0
        assert payload["proposalChangesCollapsed"] is True
        assert payload["proposalBox"] and payload["applyBox"]
        assert "i want" not in payload["proposalText"].lower()
        assert payload["applyBox"]["y"] < payload["proposalBox"]["y"] + payload["proposalBox"]["height"]
        assert payload["proposalDisabled"] is False
        assert payload["activeStep"] == "review"
        # Apply transitions canvas state out of plan-ready (plan-applied or further).
        assert payload["appliedCanvasState"] in {"plan-applied", "validating", "generating", "checking", "running", "open-app"}
        assert payload["visibleOnReview"] is True
        assert payload["thinkingVisibleOnReview"] is False
        assert payload["historyCollapsedAfterApply"] is True
        assert payload["historyScrollStyle"] == "auto"
        assert payload["historyMaxHeight"] != "none"
        assert payload["localRunReachable"] is True
        assert payload["localRunValidateEnabled"] is True
        assert payload["exportStep"] == "generate"
        assert payload["visibleOnExport"] is True
        assert payload["thinkingVisibleOnExport"] is False
        assert payload["advancedVisible"] is True
        assert payload["cliStillVisible"] is True
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

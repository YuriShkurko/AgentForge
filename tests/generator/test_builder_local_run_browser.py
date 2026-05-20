"""Browser smoke assertions for generated frontend identity checks."""
import subprocess
import sys
from pathlib import Path

import pytest


TMP_DIR = Path(__file__).resolve().parents[2] / ".tmp"
PLAYWRIGHT_DIR = TMP_DIR / "node_modules" / "playwright"


@pytest.mark.skipif(not PLAYWRIGHT_DIR.exists(), reason="Playwright browser smoke requires .tmp/node_modules/playwright")
def test_browser_smoke_rejects_blank_or_wrong_generated_frontend(tmp_path):
    script = tmp_path / "frontend-smoke.mjs"
    script.write_text(
        """
import { chromium } from '__PLAYWRIGHT_IMPORT__';
import { createServer } from 'node:http';

async function serve(html) {
  const server = createServer((req, res) => {
    res.writeHead(200, {'content-type': 'text/html'});
    res.end(html);
  });
  await new Promise((resolve, reject) => server.listen(0, '127.0.0.1', resolve).on('error', reject));
  return server;
}

async function smoke(url, expected) {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  const consoleErrors = [];
  const pageErrors = [];
  const failedRequests = [];
  page.on('console', msg => { if (msg.type() === 'error') consoleErrors.push(msg.text()); });
  page.on('pageerror', err => pageErrors.push(String(err)));
  page.on('requestfailed', req => failedRequests.push(`${req.method()} ${req.url()} ${req.failure()?.errorText || ''}`));
  try {
    await page.goto(url, { waitUntil: 'domcontentloaded' });
    const title = await page.title();
    const body = (await page.locator('body').innerText()).trim();
    const missing = expected.filter((label) => !body.includes(label) && !title.includes(label));
    return { ok: body.length > 0 && missing.length === 0 && consoleErrors.length === 0 && pageErrors.length === 0 && failedRequests.length === 0, title, body, missing, consoleErrors, pageErrors, failedRequests };
  } finally {
    await browser.close();
  }
}

const current = await serve('<!doctype html><title>Tennis Coach Ops</title><div id="root"><h1>Tennis Coach Ops</h1><nav>Clients Lessons Payments Court Vendors</nav></div>');
const wrong = await serve('<!doctype html><title>Old Vendor App</title><div id="root"></div>');
try {
  const currentResult = await smoke(`http://127.0.0.1:${current.address().port}/`, ['Tennis Coach Ops', 'Clients', 'Lessons', 'Payments', 'Court Vendors']);
  const wrongResult = await smoke(`http://127.0.0.1:${wrong.address().port}/`, ['Tennis Coach Ops', 'Clients']);
  if (!currentResult.ok) throw new Error(`expected current app smoke to pass: ${JSON.stringify(currentResult)}`);
  if (wrongResult.ok) throw new Error(`expected wrong/blank app smoke to fail: ${JSON.stringify(wrongResult)}`);
} finally {
  current.close();
  wrong.close();
}
""".replace("__PLAYWRIGHT_IMPORT__", (PLAYWRIGHT_DIR / "index.mjs").resolve().as_uri()),
        encoding="utf-8",
    )

    result = subprocess.run(["node", str(script)], text=True, capture_output=True, timeout=30)

    assert result.returncode == 0, result.stderr + result.stdout

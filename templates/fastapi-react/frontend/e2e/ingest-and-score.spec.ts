import { expect, test } from "@playwright/test";

test.beforeEach(async ({ page }) => {
  await page.goto("/");
});

test("page loads with ops panel", async ({ page }) => {
  await expect(page.getByTestId("ops-panel")).toBeVisible();
  await expect(page.getByTestId("ingest-btn")).toBeVisible();
  await expect(page.getByTestId("score-btn")).toBeVisible();
});

test("ingest creates a run row", async ({ page }) => {
  await page.getByTestId("ingest-btn").click();

  const runRow = page.getByTestId("run-row").first();
  await expect(runRow).toBeVisible({ timeout: 5000 });
  await expect(page.getByTestId("run-status").first()).toHaveText("complete");
});

test("score produces scored records", async ({ page }) => {
  await page.getByTestId("ingest-btn").click();
  await expect(page.getByTestId("run-row").first()).toBeVisible({ timeout: 5000 });

  await page.getByTestId("score-btn").click();

  const scoredRow = page.getByTestId("scored-row").first();
  await expect(scoredRow).toBeVisible({ timeout: 5000 });
});

test("scored records are ordered by fit descending", async ({ page }) => {
  await page.getByTestId("ingest-btn").click();
  await expect(page.getByTestId("run-row").first()).toBeVisible({ timeout: 5000 });
  await page.getByTestId("score-btn").click();
  await expect(page.getByTestId("scored-row").first()).toBeVisible({ timeout: 5000 });

  const fitTexts = await page.getByTestId("fit-score").allTextContents();
  const fits = fitTexts.map((t) => parseInt(t.replace("%", ""), 10));
  for (let i = 1; i < fits.length; i++) {
    expect(fits[i]).toBeLessThanOrEqual(fits[i - 1]);
  }
});

test("accept action updates badge", async ({ page }) => {
  await page.getByTestId("ingest-btn").click();
  await expect(page.getByTestId("run-row").first()).toBeVisible({ timeout: 5000 });
  await page.getByTestId("score-btn").click();
  await expect(page.getByTestId("scored-row").first()).toBeVisible({ timeout: 5000 });

  await page.getByTestId("accept-btn").first().click();

  await expect(page.getByTestId("action-badge").first()).toHaveText("accepted", { timeout: 5000 });
});

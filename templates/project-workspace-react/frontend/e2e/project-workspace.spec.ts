import { expect, test } from "@playwright/test";

test.beforeEach(async ({ page }) => {
  await page.goto("/");
});

test("project workspace golden flow", async ({ page }) => {
  await page.getByTestId("seed-btn").click();
  await expect(page.getByTestId("project-card").first()).toBeVisible({ timeout: 5000 });
  await expect(page.getByTestId("task-card").first()).toBeVisible();

  await page.getByTestId("task-status-btn").first().click();
  await expect(page.getByTestId("activity-row").first()).toContainText("task_updated", { timeout: 5000 });

  await page.getByTestId("agent-input").fill("pin task list");
  await page.getByTestId("agent-send-btn").click();
  await expect(page.getByTestId("workspace-widget").first()).toContainText("Task list", { timeout: 5000 });

  await page.reload();
  await expect(page.getByTestId("workspace-widget").first()).toContainText("Task list", { timeout: 5000 });
});

import { test, expect } from "@playwright/test";
import { login } from "./helpers";

test.describe("Kanban Board", () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
  });

  test("should display pipeline kanban board", async ({ page }) => {
    await page.goto("/kanban");
    await page.waitForLoadState("networkidle", { timeout: 30000 });

    await expect(page.locator("text=Pipeline zakázek")).toBeVisible({ timeout: 15000 });
  });
});

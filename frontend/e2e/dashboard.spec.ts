import { test, expect } from "@playwright/test";
import { login } from "./helpers";

test.describe("Dashboard", () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
  });

  test("should display dashboard stats", async ({ page }) => {
    await expect(page.locator("h1:has-text('Dashboard')")).toBeVisible({ timeout: 10000 });
    // Dashboard should have stat cards (wait for loading to complete)
    await page.waitForLoadState("networkidle", { timeout: 30000 });
    await expect(page.locator(".grid").first()).toBeVisible();
  });
});

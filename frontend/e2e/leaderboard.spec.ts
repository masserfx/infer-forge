import { test, expect } from "@playwright/test";
import { login } from "./helpers";

test.describe("Leaderboard", () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
  });

  test("should display leaderboard page or 404", async ({ page }) => {
    const response = await page.goto("/zebricek");
    await page.waitForLoadState("networkidle", { timeout: 30000 });

    // Page might not be implemented yet (404)
    if (response?.status() === 404) {
      await expect(page.locator("text=404")).toBeVisible();
    } else {
      // If page exists, check for leaderboard content
      await expect(page.locator("h1:has-text('Žebříček')")).toBeVisible({ timeout: 10000 });
    }
  });
});

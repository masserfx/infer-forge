import { test, expect } from "@playwright/test";
import { login } from "./helpers";

test.describe("Reporting", () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
  });

  test("should display reporting page", async ({ page }) => {
    await page.goto("/reporting");
    await page.waitForLoadState("networkidle", { timeout: 30000 });

    await expect(page.locator("text=Analytika a přehledy zakázek, obratu a výroby")).toBeVisible({ timeout: 15000 });
  });
});

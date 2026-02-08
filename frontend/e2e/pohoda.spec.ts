import { test, expect } from "@playwright/test";
import { login } from "./helpers";

test.describe("Pohoda", () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
  });

  test("should display pohoda page", async ({ page }) => {
    await page.goto("/pohoda");
    await page.waitForLoadState("networkidle", { timeout: 30000 });

    await expect(page.locator("text=Synchronizace s účetním systémem Pohoda")).toBeVisible({ timeout: 15000 });
  });
});

import { test, expect } from "@playwright/test";
import { login } from "./helpers";

test.describe("Calculations", () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
  });

  test("should display calculations page", async ({ page }) => {
    await page.goto("/kalkulace");
    await page.waitForLoadState("networkidle", { timeout: 30000 });

    await expect(page.locator("text=Přehled cenových kalkulací pro zakázky")).toBeVisible({ timeout: 15000 });
  });
});

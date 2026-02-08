import { test, expect } from "@playwright/test";
import { login } from "./helpers";

test.describe("Documents", () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
  });

  test("should display documents page", async ({ page }) => {
    await page.goto("/dokumenty");
    await page.waitForLoadState("networkidle", { timeout: 30000 });

    await expect(page.locator("text=Přehled všech dokumentů v systému")).toBeVisible({ timeout: 15000 });
  });
});

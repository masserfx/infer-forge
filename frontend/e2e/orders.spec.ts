import { test, expect } from "@playwright/test";
import { login } from "./helpers";

test.describe("Orders", () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
  });

  test("should display orders list", async ({ page }) => {
    await page.goto("/zakazky");
    await page.waitForLoadState("networkidle", { timeout: 30000 });
    await expect(page.locator("main h1:has-text('Zakázky')")).toBeVisible({ timeout: 10000 });
    // Should have table with orders
    await expect(page.locator("table tbody tr").first()).toBeVisible({ timeout: 10000 });
  });

  test("should navigate to order detail", async ({ page }) => {
    await page.goto("/zakazky");
    await page.waitForLoadState("networkidle", { timeout: 30000 });
    const firstRow = page.locator("table tbody tr.cursor-pointer").first();
    if (await firstRow.count() > 0) {
      await firstRow.click();
      await page.waitForLoadState("networkidle", { timeout: 30000 });
      await expect(page).toHaveURL(/zakazky\//);
      await expect(page.locator("h1:has-text('Zakázka ZAK-')")).toBeVisible({ timeout: 10000 });
    }
  });
});

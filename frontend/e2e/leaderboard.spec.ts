import { test, expect } from "@playwright/test";
import { login } from "./helpers";

test.describe("Tržiště úkolů", () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
  });

  test("should display task marketplace page", async ({ page }) => {
    await page.goto("/trziste-ukolu");
    await page.waitForLoadState("networkidle", { timeout: 30000 });

    await expect(page.locator("text=Výkonnost týmu a motivační body")).toBeVisible({ timeout: 15000 });
  });
});

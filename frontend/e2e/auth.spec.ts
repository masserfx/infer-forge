import { test, expect } from "@playwright/test";
import { login } from "./helpers";

test.describe("Authentication", () => {
  test("should login successfully", async ({ page }) => {
    await login(page);
    // Dashboard should be visible in the header
    await expect(page.locator("h1:has-text('Dashboard')")).toBeVisible({ timeout: 10000 });
  });

  test("should show error on wrong credentials", async ({ page }) => {
    await page.goto("/login");
    await page.locator('input[type="email"]').fill("wrong@test.cz");
    await page.locator('input[type="password"]').fill("wrong");
    await page.locator('button[type="submit"]').first().click();
    await page.waitForTimeout(2000);
    // Should stay on login page
    await expect(page).toHaveURL(/login/);
  });
});

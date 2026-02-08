import { test, expect } from "@playwright/test";
import { login } from "./helpers";

test.describe("Inbox", () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
  });

  test("should display inbox page", async ({ page }) => {
    await page.goto("/inbox");
    await page.waitForLoadState("networkidle", { timeout: 30000 });

    await expect(page.locator("text=AI klasifikace a přiřazení e-mailů")).toBeVisible({ timeout: 15000 });
  });
});

import { type Page, expect } from "@playwright/test";

export async function login(page: Page) {
  await page.goto("/login", { timeout: 30000 });
  await page.waitForLoadState("networkidle", { timeout: 30000 });

  // Wait for login form to be visible
  await page.locator('input[type="email"]').waitFor({ state: "visible", timeout: 10000 });

  await page.locator('input[type="email"]').fill("admin@infer.cz");
  await page.locator('input[type="password"]').fill("admin123");
  await page.locator('button[type="submit"]').first().click();

  // Wait for redirect to dashboard with longer timeout
  await page.waitForURL("**/dashboard", { timeout: 30000 });
  await expect(page).toHaveURL(/dashboard/);

  // Wait for dashboard content to load
  await page.waitForLoadState("networkidle", { timeout: 30000 });
}

export async function expectNoConsoleErrors(page: Page) {
  const errors: string[] = [];
  page.on("console", (msg) => {
    if (msg.type() === "error" && !msg.text().includes("ERR_ABORTED")) {
      errors.push(msg.text());
    }
  });
  return errors;
}

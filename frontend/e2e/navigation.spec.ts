import { test, expect } from "@playwright/test";
import { login } from "./helpers";

test.describe("Navigation", () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
  });

  test("should navigate all main pages without errors", async ({ page }) => {
    const pages = [
      { url: "/dashboard", text: "Dashboard" },
      { url: "/zakazky", text: "Zakázky" },
      { url: "/kalkulace", text: "Kalkulace" },
      { url: "/reporting", text: "Reporting" },
      { url: "/inbox", text: "Inbox" },
      { url: "/dokumenty", text: "Dokumenty" },
      { url: "/pohoda", text: "Pohoda" },
      { url: "/nastaveni", text: "Nastavení" },
    ];

    for (const p of pages) {
      const response = await page.goto(p.url);
      await page.waitForLoadState("networkidle", { timeout: 30000 });
      // Should not show application error (404 is acceptable for unimplemented pages)
      const content = await page.content();
      expect(content).not.toContain("Application error");
      // If page loads successfully (not 404), check that it has content
      if (response?.status() === 200) {
        await expect(page.locator("body")).not.toBeEmpty();
      }
    }
  });
});

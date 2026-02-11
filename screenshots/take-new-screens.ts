import { chromium } from "playwright";
import * as fs from "fs";
import * as path from "path";

const BASE_URL = "https://inferbox.hradev.cz";
const LOGIN_EMAIL = "admin@infer.cz";
const LOGIN_PASSWORD = "admin123";

const SCREENSHOTS = [
  {
    url: "/kalkulace/b8ff6c71-0b53-441c-b677-8078f502f012",
    filename: "17-kalkulace-detail.png",
  },
  {
    url: "/trziste-ukolu",
    filename: "15-trziste-ukolu.png",
  },
];

const OUTPUT_DIRS = [
  "/Users/lhradek/code/infer-forge/presentation/public/pages",
  "/Users/lhradek/code/infer-forge/screenshots/pages",
];

async function main() {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width: 1920, height: 1080 },
    deviceScaleFactor: 2,
  });
  const page = await context.newPage();

  // Login
  console.log("Navigating to login page...");
  await page.goto(`${BASE_URL}/login`, { waitUntil: "networkidle" });
  await page.waitForTimeout(1000);

  console.log("Filling login form...");
  await page.fill('input[type="email"], input[name="email"]', LOGIN_EMAIL);
  await page.fill('input[type="password"], input[name="password"]', LOGIN_PASSWORD);
  await page.click('button[type="submit"]');

  // Wait for redirect after login
  await page.waitForURL("**/dashboard**", { timeout: 15000 }).catch(() => {
    console.log("Did not redirect to dashboard, continuing anyway...");
  });
  await page.waitForLoadState("networkidle");
  await page.waitForTimeout(2000);
  console.log(`After login, current URL: ${page.url()}`);

  // Take screenshots
  for (const shot of SCREENSHOTS) {
    const targetUrl = `${BASE_URL}${shot.url}`;
    console.log(`\nNavigating to ${targetUrl}...`);
    await page.goto(targetUrl, { waitUntil: "networkidle", timeout: 30000 });
    await page.waitForTimeout(2000);
    console.log(`Current URL: ${page.url()}`);

    // Take screenshot to a temp buffer
    const buffer = await page.screenshot({ fullPage: false });

    // Save to all output directories
    for (const dir of OUTPUT_DIRS) {
      const filePath = path.join(dir, shot.filename);
      fs.writeFileSync(filePath, buffer);
      const stats = fs.statSync(filePath);
      console.log(`Saved: ${filePath} (${(stats.size / 1024).toFixed(1)} KB)`);
    }
  }

  await browser.close();
  console.log("\nDone!");
}

main().catch((err) => {
  console.error("Error:", err);
  process.exit(1);
});

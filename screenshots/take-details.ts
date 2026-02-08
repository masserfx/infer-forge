import { chromium } from 'playwright';

const BASE_URL = 'http://91.99.126.53:3000';
const DIR = '/Users/lhradek/code/work/infer/infer-forge/screenshots/pages';

async function main() {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width: 1920, height: 1080 },
    deviceScaleFactor: 2,
  });
  const page = await context.newPage();

  // Login
  await page.goto(`${BASE_URL}/login`);
  await page.fill('input[type="email"]', 'admin@infer.cz');
  await page.fill('input[type="password"]', 'admin123');
  await page.click('button[type="submit"]');
  await page.waitForURL('**/dashboard', { timeout: 15000 });
  await page.waitForTimeout(1000);

  // Get order list to find IDs
  await page.goto(`${BASE_URL}/zakazky`, { waitUntil: 'networkidle' });
  await page.waitForTimeout(1500);

  // Click on first order row (ZAK-2026-008)
  const firstRow = page.locator('tr').filter({ hasText: 'ZAK-2026-008' });
  if (await firstRow.isVisible()) {
    await firstRow.click();
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);
    await page.screenshot({ path: `${DIR}/14-zakazka-detail-top.png` });
    console.log('14-zakazka-detail-top.png');

    // Scroll to operations
    await page.evaluate(() => window.scrollTo(0, 700));
    await page.waitForTimeout(800);
    await page.screenshot({ path: `${DIR}/15-zakazka-detail-items.png` });
    console.log('15-zakazka-detail-items.png');

    await page.evaluate(() => window.scrollTo(0, 1400));
    await page.waitForTimeout(800);
    await page.screenshot({ path: `${DIR}/16-zakazka-operace.png` });
    console.log('16-zakazka-operace.png');

    await page.evaluate(() => window.scrollTo(0, 2100));
    await page.waitForTimeout(800);
    await page.screenshot({ path: `${DIR}/17-zakazka-dokumenty.png` });
    console.log('17-zakazka-dokumenty.png');

    // Full page
    await page.evaluate(() => window.scrollTo(0, 0));
    await page.waitForTimeout(500);
    await page.screenshot({ path: `${DIR}/18-zakazka-detail-full.png`, fullPage: true });
    console.log('18-zakazka-detail-full.png');
  } else {
    console.log('Order row not found, trying link approach');
    // Try clicking any text containing ZAK
    const link = page.getByText('ZAK-2026-001').first();
    if (await link.isVisible()) {
      await link.click();
      await page.waitForLoadState('networkidle');
      await page.waitForTimeout(2000);
      await page.screenshot({ path: `${DIR}/14-zakazka-detail-top.png` });
      await page.screenshot({ path: `${DIR}/18-zakazka-detail-full.png`, fullPage: true });
      console.log('14 + 18 zakazka screenshots');
    }
  }

  // Kalkulace detail
  await page.goto(`${BASE_URL}/kalkulace`, { waitUntil: 'networkidle' });
  await page.waitForTimeout(1500);
  const calcRow = page.locator('tr').filter({ hasText: 'ZAK-2026-001' });
  if (await calcRow.isVisible()) {
    await calcRow.click();
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);
    await page.screenshot({ path: `${DIR}/19-kalkulace-detail.png` });
    await page.screenshot({ path: `${DIR}/20-kalkulace-detail-full.png`, fullPage: true });
    console.log('19-20 kalkulace detail');
  }

  console.log('Done!');
  await browser.close();
}

main().catch(console.error);

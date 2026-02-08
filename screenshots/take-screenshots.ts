import { chromium } from 'playwright';

const BASE_URL = 'http://91.99.126.53:3000';
const SCREENSHOT_DIR = '/Users/lhradek/code/work/infer/infer-forge/screenshots/pages';

async function main() {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width: 1920, height: 1080 },
    deviceScaleFactor: 2,
  });
  const page = await context.newPage();

  // Login
  console.log('Logging in...');
  await page.goto(`${BASE_URL}/login`);
  await page.waitForLoadState('networkidle');
  await page.screenshot({ path: `${SCREENSHOT_DIR}/01-login.png`, fullPage: false });
  console.log('  01-login.png');

  await page.fill('input[type="email"]', 'admin@infer.cz');
  await page.fill('input[type="password"]', 'admin123');
  await page.click('button[type="submit"]');
  await page.waitForURL('**/dashboard', { timeout: 15000 });
  await page.waitForLoadState('networkidle');
  await page.waitForTimeout(1500);

  // Pages to screenshot
  const pages = [
    { path: '/dashboard', name: '02-dashboard', wait: 2000 },
    { path: '/zakazky', name: '03-zakazky', wait: 1500 },
    { path: '/kanban', name: '04-kanban', wait: 2000 },
    { path: '/kalkulace', name: '05-kalkulace', wait: 1500 },
    { path: '/dokumenty', name: '06-dokumenty', wait: 1500 },
    { path: '/reporting', name: '07-reporting', wait: 2000 },
    { path: '/inbox', name: '08-inbox', wait: 1500 },
    { path: '/materialy', name: '09-materialy', wait: 1500 },
    { path: '/subdodavatele', name: '10-subdodavatele', wait: 1500 },
    { path: '/pohoda', name: '11-pohoda', wait: 1500 },
    { path: '/zebricek', name: '12-zebricek', wait: 1500 },
    { path: '/nastaveni', name: '13-nastaveni', wait: 1500 },
  ];

  for (const p of pages) {
    console.log(`  ${p.name}...`);
    await page.goto(`${BASE_URL}${p.path}`, { waitUntil: 'networkidle', timeout: 15000 });
    await page.waitForTimeout(p.wait);
    await page.screenshot({ path: `${SCREENSHOT_DIR}/${p.name}.png`, fullPage: false });
    console.log(`  ${p.name}.png`);
  }

  // Order detail - find first order
  console.log('  Order detail...');
  await page.goto(`${BASE_URL}/zakazky`, { waitUntil: 'networkidle' });
  await page.waitForTimeout(1000);
  const orderLink = page.locator('a[href*="/zakazky/"]').first();
  if (await orderLink.isVisible()) {
    await orderLink.click();
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);
    await page.screenshot({ path: `${SCREENSHOT_DIR}/14-zakazka-detail.png`, fullPage: false });
    // Scroll down for more content
    await page.evaluate(() => window.scrollTo(0, 800));
    await page.waitForTimeout(500);
    await page.screenshot({ path: `${SCREENSHOT_DIR}/15-zakazka-detail-operace.png`, fullPage: false });
    await page.evaluate(() => window.scrollTo(0, 1600));
    await page.waitForTimeout(500);
    await page.screenshot({ path: `${SCREENSHOT_DIR}/16-zakazka-detail-dokumenty.png`, fullPage: false });
    console.log('  14-16 zakazka-detail.png');
  }

  // Calculation detail
  console.log('  Calculation detail...');
  await page.goto(`${BASE_URL}/kalkulace`, { waitUntil: 'networkidle' });
  await page.waitForTimeout(1000);
  const calcLink = page.locator('a[href*="/kalkulace/"]').first();
  if (await calcLink.isVisible()) {
    await calcLink.click();
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);
    await page.screenshot({ path: `${SCREENSHOT_DIR}/17-kalkulace-detail.png`, fullPage: false });
    console.log('  17-kalkulace-detail.png');
  }

  // Full page screenshots for key pages
  console.log('  Full page screenshots...');
  await page.goto(`${BASE_URL}/dashboard`, { waitUntil: 'networkidle' });
  await page.waitForTimeout(2000);
  await page.screenshot({ path: `${SCREENSHOT_DIR}/18-dashboard-full.png`, fullPage: true });

  await page.goto(`${BASE_URL}/reporting`, { waitUntil: 'networkidle' });
  await page.waitForTimeout(2000);
  await page.screenshot({ path: `${SCREENSHOT_DIR}/19-reporting-full.png`, fullPage: true });

  console.log('Done! All screenshots taken.');
  await browser.close();
}

main().catch(console.error);

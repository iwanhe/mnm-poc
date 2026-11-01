import { expect, Page, test } from '@playwright/test';
import { writeFileSync } from 'fs';
import { collectDiagnostics, login, navState, pageUrl } from './helpers';

/**
 * Bug: di HP, side menu terbuka lalu langsung menutup lagi (terlihat di Dashboard).
 * Test ini membuka menu lewat tombol hamburger, menunggu, lalu memastikan menu
 * masih terbuka. Timeline perubahan class body, resize, dan event theme42
 * dilampirkan supaya penyebabnya terlihat bila gagal.
 */

const PAGES = [
  { alias: 'HOME', no: 1, label: 'Dashboard (charts)' },
  { alias: 'CUSTOMERS', no: 12, label: 'Customers (tanpa chart)' },
];

async function installTimeline(page: Page) {
  await page.evaluate(() => {
    const w = window as any;
    w.__navLog = [];
    const t0 = performance.now();
    const log = (type: string, detail: unknown) =>
      w.__navLog.push({ t: Math.round(performance.now() - t0), type, detail });
    new MutationObserver(() => log('body.class', document.body.className))
      .observe(document.body, { attributes: true, attributeFilter: ['class'] });
    window.addEventListener('resize', () => log('resize', `${window.innerWidth}x${window.innerHeight}`));
    const $ = w.apex?.jQuery;
    if ($) {
      $('body').on('theme42layoutchanged', (_e: unknown, d: unknown) => log('theme42layoutchanged', d));
      $(document).on('apexwindowresized', () => log('apexwindowresized', ''));
    }
    document.addEventListener('click', (e) => {
      const el = e.target as HTMLElement;
      log('click', el.id || el.className || el.tagName);
    }, true);
  });
}

async function openNav(page: Page) {
  const toggle = page.locator('#t_Button_navControl, button.t-Button--headerTree').first();
  await expect(toggle, 'Tombol hamburger (#t_Button_navControl) tidak ditemukan').toBeVisible();
  await toggle.click();
}

for (const p of PAGES) {
  test(`side menu tetap terbuka setelah dibuka - ${p.label}`, async ({ page }, testInfo) => {
    const diag = collectDiagnostics(page);
    try {
      await login(page);
      if (p.alias !== 'HOME') {
        await page.goto(pageUrl(page.url(), p.alias, p.no));
      }
      await page.waitForLoadState('networkidle');
      await page.waitForTimeout(1000);

      const before = await navState(page);
      await installTimeline(page);

      // Pastikan mulai dari kondisi tertutup (di HP default tertutup)
      if (before.navVisible && before.expandedClass) {
        await openNav(page);
        await page.waitForTimeout(800);
        await installTimeline(page);
      }

      await openNav(page);
      await page.waitForTimeout(400);
      const justAfter = await navState(page);
      await page.screenshot({ path: testInfo.outputPath('nav-after-400ms.png') });

      await page.waitForTimeout(3000);
      const after3s = await navState(page);
      await page.screenshot({ path: testInfo.outputPath('nav-after-3s.png') });

      const timeline = await page.evaluate(() => (window as any).__navLog);
      const report = JSON.stringify({ page: p, before, justAfter, after3s, timeline }, null, 2);
      writeFileSync(testInfo.outputPath('nav-timeline.json'), report);
      await testInfo.attach('nav-timeline.json', { body: report, contentType: 'application/json' });

      expect(justAfter.navVisible, 'Menu tidak terbuka setelah klik hamburger').toBe(true);
      expect(after3s.navVisible, 'Menu menutup sendiri dalam 3 detik setelah dibuka').toBe(true);
    } finally {
      await diag.attach(testInfo);
    }
  });
}

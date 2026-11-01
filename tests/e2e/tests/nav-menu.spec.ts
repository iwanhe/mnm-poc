import { expect, Page, test } from '@playwright/test';
import { writeFileSync } from 'fs';
import { collectDiagnostics, login, navState, pageUrl } from './helpers';

/**
 * Regression test: side menu harus tetap terbuka setelah tombol hamburger ditekan.
 *
 * Latar belakang: Universal Theme 26.2.1 menutup kembali tree nav di layar < lg
 * (onExpand -> delayResize -> onResize -> collapse). MBMS memuat workaround
 * apex-static/mbms-nav-fix.js. Bila test ini gagal di HP, cek apakah file itu
 * masih dimuat (#APP_FILES#js/mbms-nav-fix.js) atau perilaku Universal Theme berubah.
 * Lihat docs/MBMS-MVP-APEXlang.md bagian 9.
 */

const PAGES = [
  { alias: 'HOME', no: 1, label: 'Dashboard' },
  { alias: 'CUSTOMERS', no: 12, label: 'Customers' },
];
const METHODS = ['click', 'tap'] as const;

/** Rekam perubahan class body dan event layout Universal Theme (untuk diagnosa bila gagal). */
async function installTimeline(page: Page) {
  await page.evaluate(() => {
    const w = window as any;
    w.__navLog = [];
    const t0 = performance.now();
    const log = (type: string, detail: unknown) =>
      w.__navLog.push({ t: Math.round(performance.now() - t0), type, detail });
    new MutationObserver(() =>
      log('body.class', document.body.className.split(' ').filter((c) => c.startsWith('js-nav')).join(' ')),
    ).observe(document.body, { attributes: true, attributeFilter: ['class'] });
    window.addEventListener('resize', () => log('resize', `${window.innerWidth}x${window.innerHeight}`));
    w.apex?.jQuery?.(document).on('theme42layoutchanged', (_e: unknown, d: unknown) => log('theme42layoutchanged', d));
  });
}

async function openNav(page: Page, method: 'click' | 'tap') {
  const toggle = page.locator('#t_Button_navControl, button.t-Button--headerTree').first();
  await expect(toggle, 'Tombol hamburger (#t_Button_navControl) tidak ditemukan').toBeVisible();
  if (method === 'tap') await toggle.tap();
  else await toggle.click();
}

for (const p of PAGES) for (const method of METHODS) {
  test(`side menu tetap terbuka setelah dibuka (${method}) - ${p.label}`, async ({ page, hasTouch }, testInfo) => {
    test.skip(method === 'tap' && !hasTouch, 'tap hanya untuk device dengan touch');
    const diag = collectDiagnostics(page);
    let report = '';
    let ok = false;
    try {
      await login(page);
      if (p.alias !== 'HOME') {
        await page.goto(pageUrl(page.url(), p.alias, p.no));
      }
      // APEX menjaga koneksi tetap terbuka, jadi 'networkidle' tidak pernah tercapai.
      await page.waitForLoadState('load');
      await expect(page.locator('.t-Body')).toBeVisible();
      await page.waitForTimeout(2000);

      // Desktop: menu bisa sudah terbuka (preferensi user). Tutup dulu agar mulai dari kondisi sama.
      const before = await navState(page);
      if (before.navVisible && before.expandedClass) {
        await openNav(page, 'click');
        await page.waitForTimeout(800);
      }

      await installTimeline(page);
      await openNav(page, method);
      await page.waitForTimeout(400);
      const justAfter = await navState(page);
      await page.waitForTimeout(3000);
      const after3s = await navState(page);
      await page.screenshot({ path: testInfo.outputPath('nav-after-3s.png') });

      const timeline = await page.evaluate(() => (window as any).__navLog);
      report = JSON.stringify({ page: p, method, before, justAfter, after3s, timeline }, null, 2);
      writeFileSync(testInfo.outputPath('nav-timeline.json'), report);
      await testInfo.attach('nav-timeline.json', { body: report, contentType: 'application/json' });

      expect(justAfter.navVisible, 'Menu tidak terbuka setelah klik hamburger').toBe(true);
      expect(after3s.navVisible, 'Menu menutup sendiri dalam 3 detik setelah dibuka').toBe(true);
      ok = true;
    } finally {
      // Log lengkap ke output job hanya bila gagal, supaya log run yang sukses tetap ringkas.
      await diag.attach(testInfo, !ok);
      if (!ok && report) {
        console.log(`\n===== nav-timeline ${testInfo.project.name} ${p.alias} ${method} =====\n${report}\n`);
      }
    }
  });
}

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
    const desc = (el: any) => {
      if (!el || !el.tagName) return String(el);
      const cls = typeof el.className === 'string' ? el.className.split(' ').slice(0, 3).join('.') : '';
      return `${el.tagName.toLowerCase()}${el.id ? '#' + el.id : ''}${cls ? '.' + cls : ''}`;
    };
    const log = (type: string, detail: unknown) =>
      w.__navLog.push({ t: Math.round(performance.now() - t0), type, detail });
    new MutationObserver(() => log('body.class', document.body.className.split(' ').filter((c: string) => c.startsWith('js-nav')).join(' ')))
      .observe(document.body, { attributes: true, attributeFilter: ['class'] });
    window.addEventListener('resize', () => log('resize', `${window.innerWidth}x${window.innerHeight}`));
    for (const type of ['pointerdown', 'pointerup', 'mousedown', 'mouseup', 'touchstart', 'touchend', 'click',
                        'focusin', 'focusout', 'keydown', 'scroll']) {
      document.addEventListener(type, (e) => log(type, desc(e.target)), true);
    }
    document.addEventListener('transitionend', (e: any) => log('transitionend', `${desc(e.target)} ${e.propertyName}`), true);
    const $ = w.apex?.jQuery;
    if ($) {
      $('body').on('theme42layoutchanged', (_e: unknown, d: unknown) => log('theme42layoutchanged', d));
      $(document).on('apexwindowresized', () => log('apexwindowresized', ''));
      $(document).on('treeviewselectionchange treeviewactivatenode', '*', (e: any) => log(e.type, desc(e.target)));
      // Tangkap siapa yang memicu expand/collapse: stack trace setiap trigger theme42layoutchanged
      const orig = $.event.trigger;
      $.event.trigger = function (event: any, data: any, elem: any, onlyHandlers: any) {
        const type = typeof event === 'string' ? event : event?.type;
        if (type === 'theme42layoutchanged') {
          log('STACK ' + JSON.stringify(data), (new Error().stack || '').split('\n').slice(2, 14).map((l: string) => l.trim()));
        }
        return orig.apply(this, arguments as any);
      };
    }
    // ringkasan nav tree untuk melihat entri yang dianggap "current"
    const tree = document.querySelector('#t_TreeNav');
    log('tree', tree ? {
      nodes: tree.querySelectorAll('li').length,
      selected: Array.from(tree.querySelectorAll('.is-selected, [aria-selected="true"], .is-current')).map(desc).slice(0, 5),
      html: tree.outerHTML.substring(0, 400),
    } : 'no #t_TreeNav');
  });
}

async function openNav(page: Page, method: 'click' | 'tap' = 'click') {
  const toggle = page.locator('#t_Button_navControl, button.t-Button--headerTree').first();
  await expect(toggle, 'Tombol hamburger (#t_Button_navControl) tidak ditemukan').toBeVisible();
  if (method === 'tap') await toggle.tap();
  else await toggle.click();
}

const METHODS = ['click', 'tap'] as const;

for (const p of PAGES) for (const method of METHODS) {
  test(`side menu tetap terbuka setelah dibuka (${method}) - ${p.label}`, async ({ page, hasTouch }, testInfo) => {
    test.skip(method === 'tap' && !hasTouch, 'tap hanya untuk device dengan touch');
    const diag = collectDiagnostics(page);
    try {
      await login(page);
      if (p.alias !== 'HOME') {
        await page.goto(pageUrl(page.url(), p.alias, p.no));
      }
      // APEX menjaga koneksi tetap terbuka, jadi 'networkidle' tidak pernah tercapai.
      await page.waitForLoadState('load');
      await expect(page.locator('.t-Body')).toBeVisible();
      await page.waitForTimeout(2000);

      const before = await navState(page);
      await installTimeline(page);

      // Pastikan mulai dari kondisi tertutup (di HP default tertutup)
      if (before.navVisible && before.expandedClass) {
        await openNav(page);
        await page.waitForTimeout(800);
        await installTimeline(page);
      }

      await openNav(page, method);
      await page.waitForTimeout(400);
      const justAfter = await navState(page);
      await page.screenshot({ path: testInfo.outputPath('nav-after-400ms.png') });

      await page.waitForTimeout(3000);
      const after3s = await navState(page);
      await page.screenshot({ path: testInfo.outputPath('nav-after-3s.png') });

      const timeline = await page.evaluate(() => (window as any).__navLog);
      const report = JSON.stringify({ page: p, method, before, justAfter, after3s, timeline }, null, 2);
      writeFileSync(testInfo.outputPath('nav-timeline.json'), report);
      // juga ke stdout supaya terbaca langsung di log GitHub Actions
      console.log(`\n===== nav-timeline ${testInfo.project.name} ${p.alias} ${method} =====\n${report}\n`);
      await testInfo.attach('nav-timeline.json', { body: report, contentType: 'application/json' });

      expect(justAfter.navVisible, 'Menu tidak terbuka setelah klik hamburger').toBe(true);
      expect(after3s.navVisible, 'Menu menutup sendiri dalam 3 detik setelah dibuka').toBe(true);
    } finally {
      await diag.attach(testInfo);
    }
  });
}

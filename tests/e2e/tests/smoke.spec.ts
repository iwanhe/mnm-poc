import { expect, test } from '@playwright/test';
import { collectDiagnostics, login, pageUrl } from './helpers';

/** Smoke test: setiap halaman utama terbuka tanpa error APEX/ORA- dan tanpa error JS. */
const PAGES: Array<{ alias: string; no: number; title: string }> = [
  { alias: 'HOME', no: 1, title: 'Dashboard' },
  { alias: 'APPROVAL-INBOX', no: 60, title: 'Approval Inbox' },
  { alias: 'JOB-ORDERS', no: 20, title: 'Job Orders' },
  { alias: 'JOB-COSTING', no: 22, title: 'Job Costing' },
  { alias: 'PROJECTS', no: 30, title: 'Projects' },
  { alias: 'WBS-BUDGET', no: 32, title: 'WBS' },
  { alias: 'PROJECT-SUMMARY', no: 34, title: 'Project Summary' },
  { alias: 'PURCHASE-REQUISITIONS', no: 40, title: 'Purchase Requisitions' },
  { alias: 'PR-LINES', no: 42, title: 'PR Lines' },
  { alias: 'STOCK-TRANSACTIONS', no: 50, title: 'Stock Transactions' },
  { alias: 'STOCK-ON-HAND', no: 52, title: 'Stock On Hand' },
  { alias: 'CUSTOMERS', no: 12, title: 'Customers' },
  { alias: 'VENDORS', no: 14, title: 'Vendors' },
  { alias: 'ITEMS', no: 16, title: 'Items' },
  { alias: 'WAREHOUSES', no: 18, title: 'Warehouses' },
];

test.describe('smoke', () => {
  test.skip(({ isMobile }) => isMobile, 'Smoke test cukup di desktop');

  test('semua halaman utama terbuka tanpa error', async ({ page }, testInfo) => {
    const diag = collectDiagnostics(page);
    const failures: string[] = [];
    try {
      await login(page);
      const base = page.url();
      for (const p of PAGES) {
        await test.step(`${p.no} ${p.alias}`, async () => {
          const before = diag.pageErrors().length;
          await page.goto(pageUrl(base, p.alias, p.no));
          await page.waitForLoadState('load');
          await page.locator('.t-Body, #P9999_USERNAME').first().waitFor({ state: 'visible' });
          await page.waitForTimeout(1500);
          const body = await page.locator('body').innerText();
          const title = await page.title();
          await page.screenshot({ path: testInfo.outputPath(`p${String(p.no).padStart(5, '0')}.png`), fullPage: true });
          if (await page.locator('#P9999_USERNAME').count()) failures.push(`${p.alias}: diarahkan ke login (sesi hilang)`);
          if (/ORA-\d{5}/.test(body)) failures.push(`${p.alias}: ${body.match(/ORA-\d{5}[^\n]*/)?.[0]}`);
          if (!title.toLowerCase().includes(p.title.toLowerCase().split(' ')[0])) failures.push(`${p.alias}: judul halaman "${title}"`);
          if (diag.pageErrors().length > before) failures.push(`${p.alias}: ${diag.pageErrors().slice(before).join(' | ')}`);
        });
      }
    } finally {
      await diag.attach(testInfo, failures.length > 0);
      await testInfo.attach('smoke-failures.txt', { body: failures.join('\n') || 'OK', contentType: 'text/plain' });
    }
    expect(failures, failures.join('\n')).toEqual([]);
  });
});

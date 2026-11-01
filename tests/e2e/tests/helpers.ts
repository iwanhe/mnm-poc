import { expect, Page, TestInfo } from '@playwright/test';
import { writeFileSync } from 'fs';

export function env(name: string): string {
  const v = process.env[name];
  if (!v) throw new Error(`Environment variable ${name} belum di-set (GitHub Secret ${name}).`);
  return v;
}

/** Kumpulkan console, error JS, dan request gagal; dilampirkan ke report di akhir test. */
export function collectDiagnostics(page: Page) {
  const logs: string[] = [];
  const ts = () => new Date().toISOString().substring(11, 23);
  page.on('console', (m) => logs.push(`${ts()} [console.${m.type()}] ${m.text()}`));
  page.on('pageerror', (e) => logs.push(`${ts()} [pageerror] ${e.message}`));
  page.on('requestfailed', (r) => logs.push(`${ts()} [requestfailed] ${r.method()} ${r.url()} ${r.failure()?.errorText}`));
  page.on('framenavigated', (f) => {
    if (f === page.mainFrame()) logs.push(`${ts()} [navigated] ${f.url()}`);
  });
  return {
    logs,
    async attach(testInfo: TestInfo) {
      writeFileSync(testInfo.outputPath('browser-log.txt'), logs.join('\n'));
      console.log(`\n===== browser-log ${testInfo.project.name} ${testInfo.title} =====\n${logs.join('\n')}\n`);
      await testInfo.attach('browser-log.txt', { body: logs.join('\n'), contentType: 'text/plain' });
    },
    pageErrors: () => logs.filter((l) => l.includes('[pageerror]')),
  };
}

/** Login lewat halaman login APEX (P9999_USERNAME / P9999_PASSWORD). */
export async function login(page: Page, url = env('APEX_APP_URL')) {
  await page.goto(url);
  const user = page.locator('#P9999_USERNAME');
  if (await user.isVisible().catch(() => false)) {
    await user.fill(env('APEX_USERNAME'));
    await page.locator('#P9999_PASSWORD').fill(env('APEX_PASSWORD'));
    await Promise.all([
      page.waitForLoadState('load'),
      page.getByRole('button', { name: /sign in/i }).click(),
    ]);
  }
  await expect(page.locator('#P9999_USERNAME'), 'Login gagal: masih di halaman login').toHaveCount(0);
  await expect(page.locator('.t-Body')).toBeVisible();
}

/**
 * URL halaman lain dalam sesi yang sama, dari URL halaman saat ini.
 * Mendukung friendly URL (/ords/r/<ws>/<app>/<alias>?session=N) dan f?p=APP:PAGE:SESSION.
 */
export function pageUrl(currentUrl: string, alias: string, pageNo: number): string {
  const u = new URL(currentUrl);
  if (u.pathname.includes('/r/')) {
    const parts = u.pathname.split('/');
    parts[parts.length - 1] = alias.toLowerCase();
    u.pathname = parts.join('/');
    const session = u.searchParams.get('session');
    u.search = session ? `?session=${session}` : '';
    return u.toString();
  }
  const p = u.searchParams.get('p') ?? '';
  const [app, , session] = p.split(':');
  u.search = `?p=${app}:${pageNo}:${session ?? ''}`;
  return u.toString();
}

/** Status side navigation menu Universal Theme. */
export async function navState(page: Page) {
  return page.evaluate(() => {
    const body = document.body;
    const nav = document.querySelector('#t_Body_nav, .t-Body-nav') as HTMLElement | null;
    const r = nav?.getBoundingClientRect();
    const visible = !!r && r.width > 40 && r.right > 40 && r.left < window.innerWidth - 10 &&
      getComputedStyle(nav!).visibility !== 'hidden';
    return {
      bodyClasses: body.className,
      expandedClass: body.classList.contains('js-navExpanded'),
      navRect: r ? { x: Math.round(r.x), w: Math.round(r.width) } : null,
      navVisible: visible,
      viewport: { w: window.innerWidth, h: window.innerHeight },
    };
  });
}

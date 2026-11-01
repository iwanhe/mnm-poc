import { defineConfig, devices } from '@playwright/test';

/**
 * Target: aplikasi MBMS di oracleapex.com (sandbox, data dummy).
 * Kredensial dari env (GitHub Secrets), tidak pernah ditulis di repo:
 *   APEX_APP_URL   URL aplikasi / halaman login, mis. https://oracleapex.com/ords/r/<workspace>/mbms
 *   APEX_USERNAME  akun khusus testing di workspace sandbox
 *   APEX_PASSWORD
 */
export default defineConfig({
  testDir: './tests',
  timeout: 90_000,
  expect: { timeout: 15_000 },
  fullyParallel: false,
  workers: 1,
  retries: 0,
  reporter: [['list'], ['html', { open: 'never' }]],
  use: {
    // Hanya untuk menjalankan lokal dengan Chromium yang sudah terpasang; di CI kosong.
    launchOptions: process.env.PW_CHROMIUM_PATH ? { executablePath: process.env.PW_CHROMIUM_PATH } : {},
    trace: 'on',
    video: process.env.PW_CHROMIUM_PATH ? 'off' : 'on',
    screenshot: 'on',
    actionTimeout: 20_000,
    navigationTimeout: 45_000,
  },
  projects: [
    {
      name: 'mobile-chrome',
      use: { ...devices['Pixel 7'] },
    },
    {
      name: 'mobile-iphone-viewport',
      // viewport & touch iPhone, tapi tetap Chromium (cukup untuk layout Universal Theme)
      use: { ...devices['iPhone 13'], browserName: 'chromium', defaultBrowserType: 'chromium' },
    },
    {
      name: 'desktop-chrome',
      use: { ...devices['Desktop Chrome'], viewport: { width: 1440, height: 900 } },
    },
  ],
});

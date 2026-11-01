# MBMS E2E (Playwright)

Test end-to-end terhadap aplikasi MBMS yang sudah di-import di oracleapex.com.

| Test | Isi |
| --- | --- |
| `nav-menu.spec.ts` | (opsional: juga aplikasi pembanding via secret `APEX_COMPARE_URL`) Buka side menu lewat hamburger, tunggu 3 detik, pastikan menu masih terbuka (Dashboard dan Customers). Menyimpan `nav-timeline.json`: class body, resize, event `theme42layoutchanged`, klik. |
| `smoke.spec.ts` | Desktop: 15 halaman utama terbuka tanpa `ORA-`, tanpa error JS, tidak terlempar ke login. |

Project: `mobile-chrome` (Pixel 7), `mobile-iphone-viewport` (viewport iPhone 13, Chromium), `desktop-chrome`.

## Jalankan di GitHub Actions

1. Repo → Settings → Secrets and variables → Actions → New repository secret:
   - `APEX_APP_URL`: URL aplikasi, mis. `https://oracleapex.com/ords/r/<workspace>/mbms`
   - `APEX_USERNAME`, `APEX_PASSWORD`: akun khusus testing di workspace sandbox
2. Actions → **E2E Playwright (oracleapex.com)** → Run workflow (pilih project atau `all`).
3. Hasil: artifact `playwright-report` berisi laporan HTML, video, trace, screenshot,
   `browser-log.txt`, dan `nav-timeline.json` per test.

## Jalankan lokal

```bash
cd tests/e2e
npm install && npx playwright install chromium
APEX_APP_URL=... APEX_USERNAME=... APEX_PASSWORD=... npx playwright test --project=mobile-chrome
```

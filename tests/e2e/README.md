# MBMS E2E (Playwright)

Test end-to-end terhadap aplikasi MBMS yang sudah di-import di oracleapex.com.

| Test | Isi |
| --- | --- |
| `nav-menu.spec.ts` | Regression test side menu: buka lewat hamburger (klik dan tap), tunggu 3 detik, pastikan menu masih terbuka. Halaman: Dashboard dan Customers. Melindungi workaround `apex-static/mbms-nav-fix.js` (bug Universal Theme 26.2.1, lihat `docs/MBMS-MVP-APEXlang.md` bagian 9). |
| `smoke.spec.ts` | Desktop: 15 halaman utama terbuka tanpa `ORA-`, tanpa error JS, dan tidak terlempar ke login. |

Project yang tersedia:

- `mobile-chrome`: Pixel 7.
- `mobile-iphone-viewport`: viewport iPhone 13, tetap memakai Chromium.
- `desktop-chrome`.

## Jalankan di GitHub Actions

1. Buka repo → Settings → Secrets and variables → Actions, lalu buat tiga secret:
   - `APEX_APP_URL`: URL aplikasi, misalnya `https://oracleapex.com/ords/r/<workspace>/mbms`.
   - `APEX_USERNAME` dan `APEX_PASSWORD`: akun khusus testing, misalnya `MBMS_E2E` dengan role `ADMIN`. Lihat README utama.
2. Buka Actions → **E2E Playwright (oracleapex.com)** → Run workflow, lalu pilih project atau `all`.
3. Hasil tersedia di artifact `playwright-report`: laporan HTML, video, trace, screenshot, `browser-log.txt`, dan `nav-timeline.json`.
   Bila ada test yang gagal, timeline dan log browser juga tercetak di log job.

## Jalankan lokal

```bash
cd tests/e2e
npm install && npx playwright install chromium
APEX_APP_URL=... APEX_USERNAME=... APEX_PASSWORD=... npx playwright test --project=mobile-chrome
```

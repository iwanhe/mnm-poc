# Blueprint Aplikasi MBMS MVP (APEXlang, APEX 26.2)

Turunan dari *Blueprint Konsolidasi MBMS v2.0* untuk sandbox oracleapex.com (Fase 0, D-14).
Isinya prototype Core Foundation plus irisan tipis Printing dan Engineering. Semua data dummy.

## 1. Isi repository

| Path | Isi |
| --- | --- |
| `apex/mbms/` | Source aplikasi APEXlang (satu source untuk semua environment, K-05) |
| `dist/mbms-apexlang.zip` | Zip siap upload ke App Builder → Import |
| `database/install/01..05_*.sql` | DDL, package, trigger, view, seed (urutan eksekusi) |
| `database/mbms_install.sql` | Gabungan 01–05 untuk SQL Workshop → SQL Scripts |
| `database/install/99_deinstall.sql` | Hapus semua objek MBMS (sandbox saja) |
| `tools/apexgen/` | Generator scaffold `.apx` + pemeriksa struktural |
| `scripts/` | `build-install-sql.sh`, `package-apex.sh` |

## 2. Cara upload ke oracleapex.com

1. **SQL Workshop → SQL Scripts → Upload** `database/mbms_install.sql`, lalu **Run**. Pastikan 0 error.
   Tabel harus ada sebelum import, karena form dan report memakai tabel/view ini.
2. **App Builder → Import** → pilih `dist/mbms-apexlang.zip`. APEX memvalidasi dan mengompilasi APEXlang saat import.
3. Jalankan aplikasi dan login dengan akun workspace.
4. Buka **Administration → Users & Roles**. Daftarkan username Anda sebagai `ADMIN`.
   Selama belum ada ADMIN, semua user dianggap ADMIN (mode bootstrap).
5. Untuk uji approval, buat user workspace kedua lalu beri role approver (`PRINT_MGR`, `ENG_MGR`, `PROCUREMENT`, `DIRECTOR`).
   Pengaju tidak boleh menyetujui dokumennya sendiri (maker-checker).

Validasi offline sebelum upload (Blueprint 8.5 langkah 3):

```bash
export SQLCL_BIN=/path/to/sqlcl/bin/sql
.claude/skills/apexlang/26.2/apexlang-compile/scripts/validate-apex-app.sh apex/mbms
```

## 3. Cakupan modul

| Kelompok | Fitur MVP | Halaman |
| --- | --- | --- |
| Dashboard | KPI (approval menunggu, job/proyek aktif, PR terbuka, item di bawah min. stok), 4 chart | 1 |
| Master Data | Business Unit, Customer (NPWP/NITKU), Vendor (barang/subkon/jasa), Item, Gudang & lokasi (site/vendor) | 10–19 |
| Printing | Job Order MTO/Stok, imposition, toleransi insheet, estimasi HPP 7 komponen, realisasi produksi; Job Costing estimasi vs aktual | 20–22 |
| Engineering | Project, WBS & budget vs actual/committed, Project Summary (retensi, peringatan rugi, keterlambatan) | 30–34 |
| Procurement | Purchase Requisition (stok/job/proyek) dengan baris item dan budget check | 40–43 |
| Inventory | Stock ledger (receipt, issue, return, adjustment), Stock On Hand + nilai rata-rata | 50–52 |
| Approval | Inbox dan aksi approve/reject, 2 level berdasarkan limit | 60–61 |
| Administration | Users & Roles, Document Types (prefix nomor + approval matrix) | 90–93 |

## 4. Model data

| Domain | Tabel / View |
| --- | --- |
| SYS | `SYS_ROLE`, `SYS_USER_ROLE`, `SYS_DOC_TYPE`, `SYS_DOC_SEQ`, `SYS_APPROVAL`, view `SYS_APPROVAL_V` |
| MDM | `MDM_BUSINESS_UNIT`, `MDM_CUSTOMER`, `MDM_VENDOR`, `MDM_ITEM`, `MDM_WAREHOUSE` |
| PRT | `PRT_JOB_ORDER` (kolom virtual `EST_HPP`), view `PRT_JOB_COST_V` |
| PRJ | `PRJ_PROJECT`, `PRJ_WBS`, view `PRJ_WBS_BUDGET_V`, `PRJ_PROJECT_SUMMARY_V` |
| PUR | `PUR_REQUISITION`, `PUR_REQUISITION_LINE`, view `PUR_REQUISITION_V`, `PUR_REQUISITION_LINE_V` |
| INV | `INV_STOCK_TXN` (ledger), view `INV_STOCK_TXN_V`, `INV_STOCK_ON_HAND_V` |

Package PL/SQL (semua logika bisnis di database, Blueprint 7.1):

| Package | Fungsi |
| --- | --- |
| `MBMS_SEC` | `has_role` / `has_role_yn`; dipakai authorization scheme APEX |
| `MBMS_DOC` | `next_no`; nomor dokumen `PREFIX-BU-YYYY-NNNN`, misalnya `JO-PRT-2026-0001` |
| `MBMS_INV` | `on_hand`, `avg_cost` (moving average) |
| `MBMS_APPROVAL` | `submit`, `approve`, `reject`, `can_act_yn`; engine generik untuk JO, PRJ, PR |

## 5. Business rule yang ditegakkan di database

| Rule | Implementasi |
| --- | --- |
| BR-01 BU identification | `BU_ID` wajib di job, proyek, PR, dan gudang; transaksi stok mewarisi BU dari gudang |
| BR-02 Approval | Status dokumen hanya berubah lewat `MBMS_APPROVAL`; trigger menolak perubahan langsung dan mengunci dokumen berstatus SUBMITTED |
| BR-03 Budget control | Submit PR proyek ditolak bila nilai PR > budget − aktual − committed |
| BR-05 Cost traceability | Issue/return wajib ke job atau proyek yang sudah APPROVED; biaya masuk ke job costing / WBS |
| BR-07 Stock accuracy | Stok hanya dari ledger; stok tidak boleh minus; transaksi yang sudah diposting tidak bisa diubah atau dihapus (koreksi lewat ADJ/RETURN) |
| BR-09 Change management | Estimasi job, nilai kontrak, dan budget WBS terkunci setelah approval |
| BR-12 Subcontract | Lokasi vendor subkon dan site proyek tercatat sebagai gudang tipe `VENDOR` / `SITE` di bawah BU |
| Maker-checker | Approver ≠ pengaju; reject wajib disertai alasan |

## 6. Alur demo

1. **Printing:** Job Orders → Create → isi estimasi → Create → buka lagi → Submit for Approval.
   User `PRINT_MGR` → Approval Inbox → Approve. Gudang → Stock Transactions → ISSUE kertas ke job.
   Job Costing menampilkan HPP estimasi vs aktual.
2. **Engineering:** Projects → Create → WBS & Budget → tambah WBS → Submit proyek.
   `ENG_MGR` approve. Bila budget > 100 juta, lanjut ke `DIRECTOR`.
3. **Procurement:** PR tujuan PROJECT → tambah baris di PR Lines → Submit.
   Budget dicek otomatis, lalu approval `PROCUREMENT` (dan `DIRECTOR` bila > 50 juta).

Seed sudah berisi job order brosur 10.000 lembar (APPROVED) dan proyek conveyor dengan 6 WBS sesuai contoh blueprint, lengkap dengan material issue dan satu PR draft.

## 7. Di luar MVP

Ditunda ke fase berikutnya:

- PO, goods receipt dari PO, 3-way match
- Finance/GL dan pajak
- PPC dan scheduling mesin
- QC
- Subcontract order
- Change order
- Timesheet
- Progress billing PSAK 72
- DMS
- REST/ORDS
- ACL APEX

Approval engine, penomoran, dan pola package di sini menjadi fondasinya.

## 8. Catatan teknis

- Aplikasi dibuat dari template `example-0` skill APEXlang 26.2 (theme Universal Theme subscribed, `mmdVersion 26.2.0+3479`).
- `tools/apexgen/gen_mbms.py` hanya untuk scaffold baseline. Setelah aplikasi diubah lewat Page Designer, export ulang dari APEX dalam format APEXlang lalu commit. Export itulah sumber kebenaran.
- `tools/apexgen/check_apx.py` memeriksa struktur (blok, satu properti per baris, referensi `@`). Pemeriksa ini **bukan** pengganti `apex validate`.
- Supporting objects tidak dipakai. DDL dijalankan terpisah supaya bisa diputar ulang di server kantor lewat SQLcl Projects (K-06).

## 9. Known issue: side menu di layar HP (Universal Theme 26.2.1)

Di layar yang lebih sempit dari breakpoint `lg`, side navigation menu langsung menutup lagi setelah dibuka. Ini terjadi juga di aplikasi wizard/starter app Oracle (Strategic Planner) di instance yang sama.

**Penyebab** (dibuktikan lewat E2E Playwright, run #4–#5):

- `onExpand` tree nav memanggil `delayResize()`.
- Resize sintetis itu ditangkap `onResize`, yang memanggil `collapse()` bila lebar layar di bawah `lg`.

**Workaround:** `apex-static/mbms-nav-fix.js`, dimuat app-wide sebagai static file `#APP_FILES#js/mbms-nav-fix.js`.

- Selama 800 ms setelah menu dibuka, event resize sintetis pada `window` diabaikan, tapi hanya jika ukuran viewport tidak berubah.
- Resize sungguhan seperti rotasi layar tetap diproses.
- Diverifikasi di oracleapex.com: semua varian `+fix` lolos, varian tanpa fix gagal.

Hapus file dan referensinya di `application.apx` (generator: `tools/apexgen/gen_mbms.py`) bila Oracle sudah memperbaiki Universal Theme.

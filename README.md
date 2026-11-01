# MBMS: Multisarana Business Management System (MVP)

Prototype MVP sistem ERP **PT. Multisarana Niaga Mandiri** di **Oracle APEX 26.2** (APEXlang), untuk sandbox **oracleapex.com**. Isinya sebagai berikut.

- **Shared core**
  - Master data
  - Approval engine
  - Penomoran dokumen
  - Stock ledger
- **Printing (Job Manufacturing)**
  - Job order
  - Estimasi HPP
  - Actual job costing
- **Engineering (Project Cost Control)**
  - Proyek
  - WBS budget vs actual
  - Retensi
- **Procurement**
  - Purchase requisition dengan budget check

Semua data di repo ini **dummy**. Jangan memasukkan data nyata MNMM ke sandbox.

Rancangan lengkap ada di [`docs/MBMS-MVP-APEXlang.md`](docs/MBMS-MVP-APEXlang.md): modul, model data, business rule, dan known issue.

---

## Isi repository

| Path | Isi |
| --- | --- |
| `apex/mbms/` | Source aplikasi APEXlang: 34 halaman, shared components, theme |
| `dist/mbms-apexlang.zip` | Zip siap import ke App Builder |
| `database/mbms_install.sql` | Script instalasi gabungan (tabel, package, trigger, view, data dummy) untuk SQL Workshop |
| `database/install/0*.sql` | Sumber script per bagian, dijalankan berurutan |
| `database/install/99_deinstall.sql` | Menghapus semua objek MBMS (sandbox saja) |
| `apex-static/mbms-nav-fix.js` | Workaround side menu di HP (bug Universal Theme 26.2.1) |
| `tools/apexgen/` | Generator scaffold `.apx` dan pemeriksa struktur |
| `scripts/` | `build-install-sql.sh` (gabung SQL), `package-apex.sh` (buat zip) |
| `tests/e2e/` | Test Playwright: regression side menu dan smoke test halaman |
| `.github/workflows/` | `validate-apex.yml` (SQLcl `apex validate`), `e2e-playwright.yml` (E2E ke oracleapex.com) |
| `.claude/skills/apexlang/` | Skill APEXlang resmi dari [oracle/skills](https://github.com/oracle/skills) (26.1 dan 26.2) |

---

## Instalasi di oracleapex.com

### Prasyarat

- Workspace di [oracleapex.com](https://oracleapex.com) yang menjalankan APEX **26.2**. Cek di Help → About.
- Akun Anda adalah **workspace administrator**, karena hanya admin yang bisa membuat user.

### 1. Pasang objek database

1. Buka **SQL Workshop → SQL Scripts → Upload**, lalu pilih [`database/mbms_install.sql`](database/mbms_install.sql).
2. Klik **Run**, lalu periksa hasilnya. Semua statement harus sukses (0 error).

Script ini membuat:

- 16 tabel (`SYS_`, `MDM_`, `PRT_`, `PRJ_`, `PUR_`, `INV_`)
- 4 package: `MBMS_SEC`, `MBMS_DOC`, `MBMS_INV`, `MBMS_APPROVAL`
- trigger business rule
- 8 view
- data dummy:
  - 2 BU, 4 gudang/lokasi, 3 customer, 4 vendor, 7 item
  - stok awal
  - job order brosur 10.000 lembar (APPROVED) dan 1 job draft
  - proyek conveyor dengan 6 WBS (APPROVED)
  - material issue
  - 1 PR draft

> **Instal ulang dari nol:** jalankan dulu `database/install/99_deinstall.sql`, baru `mbms_install.sql`. Semua data MBMS akan terhapus.

### 2. Import aplikasi

1. Buka **App Builder → Import**, lalu pilih [`dist/mbms-apexlang.zip`](dist/mbms-apexlang.zip) apa adanya, tanpa diekstrak.
2. Bila aplikasi sudah ada, pilih **Replace Existing Application**.
3. Jalankan aplikasi. Login memakai **akun workspace APEX** (authentication: Oracle APEX Accounts).

> Bila import gagal dengan `ORDS Authentication request failed. Reason: Not Found`, buka **SQL Workshop → RESTful Services**. Klik **Register Schema with ORDS** bila tombol itu tersedia, lalu ulangi import.

### 3. Buat user workspace

Hak akses MBMS memakai **role di tabel `SYS_USER_ROLE`**, bukan ACL APEX. Setiap orang tetap butuh **akun workspace APEX** untuk login.

1. Buka menu user (kanan atas) → **Administration** → **Manage Users and Groups** → **Create User**.
2. Isi **Username**, **Email**, dan **Password**.
3. Untuk sandbox, set *Require Change of Password on First Use* = **No**.

Buat user berikut. Nama di bawah ini adalah saran, boleh diganti asal konsisten di langkah 4.

| Username | Role MBMS | Dipakai untuk |
| --- | --- | --- |
| `MBMS_ADMIN` | `ADMIN` | Kelola user & role, master data, document type. Boleh memakai akun Anda sendiri. |
| `MBMS_SALES` | `SALES` | Customer, membuat & submit Job Order |
| `MBMS_PRINT_MGR` | `PRINT_MGR` | Approve Job Order, update progres produksi |
| `MBMS_PM` | `PROJECT_MGR` | Membuat proyek, WBS & budget, submit budget, membuat PR proyek |
| `MBMS_ENG_MGR` | `ENG_MGR` | Approve budget proyek (level 1) |
| `MBMS_DIRECTOR` | `DIRECTOR` | Approval level 2: budget proyek > 100 jt, PR > 50 jt |
| `MBMS_PROC` | `PROCUREMENT` | Approve PR (level 1), kelola vendor & item |
| `MBMS_WH` | `WAREHOUSE` | Transaksi stok: receipt, issue, return, adjustment |
| `MBMS_FIN` | `FINANCE` | Lihat costing, kelola master data |
| `MBMS_E2E` | *(tidak perlu role)* | Akun khusus test otomatis Playwright (opsional) |

Ringkasan hak akses per role (Blueprint 6.2):

| Area | Role yang diizinkan |
| --- | --- |
| Form master data | `ADMIN`, `FINANCE`, `PROCUREMENT`, `SALES` |
| Form Job Order | `PRINT_MGR`, `SALES`, `DIRECTOR` |
| Form Project & WBS | `PROJECT_MGR`, `ENG_MGR`, `DIRECTOR` |
| Form Stock Transaction | `WAREHOUSE` |
| Purchase Requisition | semua user yang login |
| Administration | `ADMIN` |
| Halaman laporan/daftar | semua user yang login |

Aturan yang berlaku untuk semua role:

- Role `ADMIN` otomatis lolos semua pemeriksaan role.
- **Maker-checker** selalu berlaku: pengaju tidak bisa menyetujui dokumennya sendiri, termasuk bila ia ADMIN.

### 4. Daftarkan role di aplikasi

1. Login ke MBMS sebagai `MBMS_ADMIN`.
   > **Mode bootstrap:** selama belum ada satu pun user ber-role `ADMIN`, semua user dianggap ADMIN. Ini supaya admin pertama bisa mendaftarkan dirinya sendiri.
2. Buka **Administration → Users & Roles → Create**.
3. Daftarkan **`MBMS_ADMIN` sebagai `ADMIN` terlebih dahulu**. Setelah itu mode bootstrap berakhir.
4. Daftarkan user lain sesuai tabel di langkah 3. Username harus sama persis dengan username workspace. Huruf besar/kecil tidak berpengaruh.

Satu user boleh punya lebih dari satu role: buat satu baris per role.

---

## Simulasi (alur demo)

Jalankan skenario berikut setelah instalasi. Gunakan **browser/jendela private berbeda** untuk tiap user, supaya sesinya tidak tercampur.

### A. Printing: Job Order → Approval → Material Issue → Job Costing

| # | User | Langkah | Hasil yang diharapkan |
| --- | --- | --- | --- |
| 1 | `MBMS_SALES` | **Printing → Job Orders** → buka job **"Kemasan karton lipat 3 warna"** (DRAFT). Periksa imposition, toleransi insheet, dan estimasi biaya, lalu klik **Submit for Approval**. | Status menjadi `SUBMITTED`; field estimasi terkunci. |
| 2 | `MBMS_SALES` | Buka **Approval Inbox**. | Dokumen tampil, tetapi **Bisa Saya Proses = N**. Pengaju tidak bisa approve sendiri. |
| 3 | `MBMS_PRINT_MGR` | **Approval Inbox** → buka dokumen JO → **Approve**. | JO menjadi `APPROVED`. Est. HPP 11,7 jt < limit, jadi tidak ada level 2. |
| 4 | `MBMS_WH` | **Inventory → Stock Transactions → Create**: tipe **ISSUE**, gudang `WH-PRINT`, item `PRT-PAP-AP150`, qty `1300`, Job Order = job tadi. Biaya satuan dikosongkan. | Nomor `MI-PRT-2026-xxxx` terbentuk; biaya dihitung dari rata-rata (1.600/lembar). |
| 5 | `MBMS_WH` | Coba ISSUE `PRT-PAP-AP150` qty `999999`. | Ditolak: **"Stok tidak cukup"**. |
| 6 | `MBMS_PRINT_MGR` | Buka JO → ubah Status ke `IN_PROGRESS`, isi Qty Produced `5000` dan Qty Reject `150`. | Tersimpan; spesifikasi & estimasi tetap terkunci. |
| 7 | siapa saja | **Printing → Job Costing (HPP)**. | Est. HPP vs HPP aktual, varians, waste % vs toleransi, dan margin per job. |

### B. Engineering: Proyek → Budget WBS → Approval 2 level

| # | User | Langkah | Hasil yang diharapkan |
| --- | --- | --- | --- |
| 1 | `MBMS_PM` | **Engineering → Projects → Create**: nama "Ducting Pabrik Bekasi", customer `C-0002`, nilai kontrak `150.000.000`, retensi 5%. Klik **Create**. | Nomor `PJ-ENG-2026-xxxx`, status `DRAFT`. |
| 2 | `MBMS_PM` | **WBS & Budget vs Actual → Create** untuk proyek tersebut. Tambahkan beberapa WBS dengan total **> 100 jt**, misalnya 1.0 Design 15 jt, 2.0 Material 70 jt, 3.0 Fabrikasi 30 jt. | Budget per WBS tampil. |
| 3 | `MBMS_PM` | Buka proyek → **Submit for Approval**. | Status `SUBMITTED`; budget WBS terkunci. |
| 4 | `MBMS_ENG_MGR` | **Approval Inbox** → Approve (level 1). | Muncul approval **level 2** untuk `DIRECTOR`, karena budget 115 jt > 100 jt. |
| 5 | `MBMS_DIRECTOR` | **Approval Inbox** → Approve (level 2). | Proyek menjadi `APPROVED`. |
| 6 | siapa saja | **Project Summary**. | Nilai kontrak, retensi, budget, aktual, planned margin, peringatan rugi/terlambat. |

Variasi penolakan: di langkah 4, klik **Reject**. Catatan wajib diisi. Proyek kembali `REJECTED` dan bisa diedit lalu diajukan ulang.

### C. Procurement: PR proyek dengan budget control (BR-03)

Dari data dummy, sisa anggaran WBS 2.0 proyek conveyor adalah **80 jt − 42,8 jt (aktual) = 37,2 jt**.

| # | User | Langkah | Hasil yang diharapkan |
| --- | --- | --- | --- |
| 1 | `MBMS_PM` | **Procurement → Purchase Requisitions** → buka PR draft "Tambahan material frame conveyor". Klik angka **Jml Baris** untuk melihat 2 baris (7,4 jt). Kembali, lalu **Submit for Approval**. | Lolos cek anggaran; status `SUBMITTED`. |
| 2 | `MBMS_PROC` | **Approval Inbox** → Approve. | PR `APPROVED`. Nilai 7,4 jt < 50 jt, jadi tanpa level 2. |
| 3 | `MBMS_PM` | Buat PR baru: tujuan **Engineering Project**, proyek conveyor, WBS **2.0**. Di **PR Lines** tambahkan item `ENG-STL-PLT6` qty `15` × `2.100.000` (31,5 jt). Lalu Submit. | Ditolak: **"Anggaran tidak cukup. Sisa anggaran: 29,800,000, nilai PR: 31,500,000"** (37,2 jt − 7,4 jt committed). Pemisah ribuan mengikuti NLS database. |
| 4 | siapa saja | **WBS & Budget vs Actual**. | Kolom Aktual, Committed (PR), dan Sisa Anggaran per WBS. |

### D. Kontrol yang bisa dicoba

- **Transaksi stok tidak bisa diubah/dihapus.** Koreksi dilakukan dengan transaksi `ADJ_IN`/`ADJ_OUT`/`RETURN` (reversal, BR-07).
- **Issue material ke job/proyek yang belum approved** ditolak (BR-05).
- **Dokumen berstatus `SUBMITTED`** tidak bisa diedit; tombol simpan hilang dan database juga menolak (BR-02).
- **Penomoran dokumen** mengikuti format `PREFIX-BU-TAHUN-NNNN`. Prefix dan approval matrix bisa diubah di **Administration → Document Types & Approval** (D-11).
- **Menu di HP** tetap terbuka setelah tombol ☰ ditekan (workaround Universal Theme 26.2.1).

---

## CI/CD dan test otomatis

| Workflow | Kapan | Isi |
| --- | --- | --- |
| **Validate APEXlang** (`validate-apex.yml`) | Push ke `main`/`claude/**` atau PR yang mengubah `apex/` | Pemeriksaan struktur, SQLcl `apex validate` (tanpa database), lalu artifact zip siap import |
| **E2E Playwright** (`e2e-playwright.yml`) | Manual (Run workflow), setelah import versi baru | Regression side menu di HP/desktop dan smoke test 15 halaman ke aplikasi di oracleapex.com |

Secret untuk E2E (Settings → Secrets and variables → Actions):

- `APEX_APP_URL`: URL aplikasi, misalnya `https://oracleapex.com/ords/r/<workspace>/mbms`.
- `APEX_USERNAME` / `APEX_PASSWORD`: sebaiknya `MBMS_E2E`.

Detail ada di [`tests/e2e/README.md`](tests/e2e/README.md).

---

## Pengembangan

1. Ubah `tools/apexgen/gen_mbms.py` (halaman, LOV, menu) atau `database/install/0*.sql`.
2. Regenerate dan cek:
   ```bash
   python3 tools/apexgen/gen_mbms.py              # tulis ulang apex/mbms
   python3 tools/apexgen/check_apx.py apex/mbms   # cek struktur
   scripts/build-install-sql.sh                   # gabung SQL → database/mbms_install.sql
   scripts/package-apex.sh                        # zip → dist/mbms-apexlang.zip
   ```
3. Push. GitHub Actions menjalankan `apex validate`.
4. Import zip ke oracleapex.com, lalu jalankan workflow E2E.

> Generator hanya untuk baseline. Bila aplikasi sudah diubah lewat Page Designer, **export ulang dari APEX** (format APEXlang), lalu commit ke `apex/mbms`. Setelah itu export menjadi sumber kebenaran, dan generator tidak dipakai lagi untuk bagian yang sudah diubah.

## Known issues

- **Side menu di HP menutup sendiri:** bug Universal Theme 26.2.1, diatasi dengan `apex-static/mbms-nav-fix.js`. Lihat [`docs/MBMS-MVP-APEXlang.md`](docs/MBMS-MVP-APEXlang.md) bagian 9.
- **Di luar MVP:**
  - PO, GR dari PO, 3-way match
  - GL/pajak
  - PPC & scheduling mesin
  - QC
  - Subkon
  - Change order
  - Timesheet
  - Progress billing PSAK 72

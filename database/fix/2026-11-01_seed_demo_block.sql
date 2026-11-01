-- MBMS MVP - Perbaikan seed: jalankan HANYA blok data contoh (dummy).
-- Untuk database yang sudah menjalankan mbms_install.sql versi lama dan gagal di blok ini
-- (PLS-00231). Semua objek dan master data lain sudah terpasang.

-- Contoh transaksi (dummy) -----------------------------------------------------
-- Catatan: fungsi lokal PL/SQL tidak boleh dipanggil di dalam SQL (PLS-00231),
-- jadi lookup ID dilakukan di prosedur lokal sebelum INSERT.
declare
   l_prt   number;
   l_eng   number;
   l_c1    number;
   l_c2    number;
   l_c3    number;
   l_job   number;
   l_prj   number;
   l_wbs2  number;
   l_pr    number;

   procedure txn (p_type varchar2, p_wh varchar2, p_item varchar2, p_qty number,
                  p_cost number default null, p_job number default null,
                  p_prj number default null, p_wbs number default null, p_ref varchar2 default null) is
      l_wh   number;
      l_item number;
   begin
      select warehouse_id into l_wh from mdm_warehouse where wh_code = p_wh;
      select item_id into l_item from mdm_item where item_code = p_item;
      insert into inv_stock_txn (txn_type, warehouse_id, item_id, qty, unit_cost, job_id, project_id, wbs_id, reference)
      values (p_type, l_wh, l_item, p_qty, p_cost, p_job, p_prj, p_wbs, p_ref);
   end txn;

   procedure pr_line (p_pr number, p_item varchar2, p_qty number, p_price number) is
      l_item number;
   begin
      select item_id into l_item from mdm_item where item_code = p_item;
      insert into pur_requisition_line (pr_id, item_id, qty, unit_price) values (p_pr, l_item, p_qty, p_price);
   end pr_line;
begin
   select bu_id into l_prt from mdm_business_unit where bu_code = 'PRT';
   select bu_id into l_eng from mdm_business_unit where bu_code = 'ENG';
   select customer_id into l_c1 from mdm_customer where customer_code = 'C-0001';
   select customer_id into l_c2 from mdm_customer where customer_code = 'C-0002';
   select customer_id into l_c3 from mdm_customer where customer_code = 'C-0003';

   -- Penerimaan stok awal
   txn('RECEIPT', 'WH-PRINT', 'PRT-PAP-AP150', 20000, 1600, p_ref => 'Saldo awal (dummy)');
   txn('RECEIPT', 'WH-PRINT', 'PRT-INK-CMYK', 50, 120000, p_ref => 'Saldo awal (dummy)');
   txn('RECEIPT', 'WH-PRINT', 'PRT-PLT-CTP', 100, 100000, p_ref => 'Saldo awal (dummy)');
   txn('RECEIPT', 'WH-ENG', 'ENG-STL-UNP100', 60, 650000, p_ref => 'Saldo awal (dummy)');
   txn('RECEIPT', 'WH-ENG', 'ENG-STL-PLT6', 15, 2100000, p_ref => 'Saldo awal (dummy)');
   txn('RECEIPT', 'WH-ENG', 'ENG-CON-ELD', 80, 45000, p_ref => 'Saldo awal (dummy)');

   -- Job order contoh 10.000 brosur (Blueprint 3.3), langsung APPROVED untuk demo
   mbms_approval.set_bypass(true);
   insert into prt_job_order (bu_id, customer_id, job_type, product_desc, qty_order, ups_per_sheet, insheet_pct,
                              due_date, selling_price, est_paper, est_ink, est_plate, est_machine, est_finishing,
                              est_labor, est_overhead, status)
   values (l_prt, l_c1, 'MTO', 'Brosur A4 4/4 Art Paper 150gsm, laminasi doff', 10000, 4, 5,
           trunc(sysdate) + 14, 19500000, 8000000, 1200000, 800000, 2000000, 1500000, 500000, 1000000, 'APPROVED')
   returning job_id into l_job;

   insert into prt_job_order (bu_id, customer_id, job_type, product_desc, qty_order, ups_per_sheet, insheet_pct,
                              due_date, selling_price, est_paper, est_ink, est_plate, est_machine, est_finishing,
                              est_labor, est_overhead, status)
   values (l_prt, l_c2, 'MTO', 'Kemasan karton lipat 3 warna', 5000, 2, 7,
           trunc(sysdate) + 21, 14000000, 6000000, 900000, 600000, 1800000, 1200000, 400000, 800000, 'DRAFT');

   -- Proyek conveyor contoh (Blueprint 4.4), langsung APPROVED untuk demo
   insert into prj_project (bu_id, customer_id, project_name, project_type, contract_value, retention_pct,
                            start_date, end_date, progress_pct, project_manager, status)
   values (l_eng, l_c3, 'Conveyor System Gudang Karawang', 'FABRICATION', 230000000, 5,
           trunc(sysdate) - 30, trunc(sysdate) + 60, 25, 'PM.DUMMY', 'APPROVED')
   returning project_id into l_prj;

   insert into prj_wbs (project_id, wbs_code, wbs_name, cost_category, budget_amount) values (l_prj, '1.0', 'Engineering & Design', 'LABOR', 15000000);
   insert into prj_wbs (project_id, wbs_code, wbs_name, cost_category, budget_amount) values (l_prj, '2.0', 'Procurement Material', 'MATERIAL', 80000000) returning wbs_id into l_wbs2;
   insert into prj_wbs (project_id, wbs_code, wbs_name, cost_category, budget_amount) values (l_prj, '3.0', 'Workshop Fabrication', 'LABOR', 40000000);
   insert into prj_wbs (project_id, wbs_code, wbs_name, cost_category, budget_amount) values (l_prj, '4.0', 'Surface Treatment', 'SUBCON', 10000000);
   insert into prj_wbs (project_id, wbs_code, wbs_name, cost_category, budget_amount) values (l_prj, '5.0', 'Site Installation', 'SUBCON', 30000000);
   insert into prj_wbs (project_id, wbs_code, wbs_name, cost_category, budget_amount) values (l_prj, '6.0', 'Testing & Commissioning', 'OTHER', 10000000);
   mbms_approval.set_bypass(false);

   -- Material issue ke job dan proyek (biaya = rata-rata, dihitung trigger)
   txn('ISSUE', 'WH-PRINT', 'PRT-PAP-AP150', 2650, p_job => l_job, p_ref => 'Issue kertas + insheet 5%');
   txn('ISSUE', 'WH-PRINT', 'PRT-INK-CMYK', 8, p_job => l_job, p_ref => 'Issue tinta');
   txn('ISSUE', 'WH-ENG', 'ENG-STL-UNP100', 40, p_prj => l_prj, p_wbs => l_wbs2, p_ref => 'Frame conveyor');
   txn('ISSUE', 'WH-ENG', 'ENG-STL-PLT6', 8, p_prj => l_prj, p_wbs => l_wbs2, p_ref => 'Plat dudukan');

   -- PR draft untuk proyek
   insert into pur_requisition (bu_id, purpose, project_id, wbs_id, need_date, description)
   values (l_eng, 'PROJECT', l_prj, l_wbs2, trunc(sysdate) + 7, 'Tambahan material frame conveyor')
   returning pr_id into l_pr;
   pr_line(l_pr, 'ENG-STL-UNP100', 10, 650000);
   pr_line(l_pr, 'ENG-CON-ELD', 20, 45000);
exception
   when others then
      mbms_approval.set_bypass(false);
      raise;
end;
/

commit;

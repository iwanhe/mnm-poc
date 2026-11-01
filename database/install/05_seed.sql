-- =============================================================================
-- MBMS MVP - 05 Seed data
-- Konfigurasi (role, jenis dokumen, BU, gudang) + DATA DUMMY untuk sandbox.
-- Tidak ada data nyata MNMM di sandbox (Blueprint 8.5).
-- =============================================================================

-- Roles (Blueprint 6.2) --------------------------------------------------------
insert into sys_role values ('ADMIN',       'IT Admin',          'Administrasi teknis, user & role');
insert into sys_role values ('DIRECTOR',    'Director',          'View dan approval level 2');
insert into sys_role values ('PRINT_MGR',   'Printing Manager',  'Operasional Printing, approval job order');
insert into sys_role values ('PROJECT_MGR', 'Project Manager',   'Operasional Engineering');
insert into sys_role values ('ENG_MGR',     'Engineering Manager','Approval budget proyek & change order');
insert into sys_role values ('PROCUREMENT', 'Procurement',       'PR/PO, approval PR');
insert into sys_role values ('WAREHOUSE',   'Warehouse',         'Transaksi stok');
insert into sys_role values ('FINANCE',     'Finance',           'Costing & keuangan');
insert into sys_role values ('SALES',       'Sales',             'Customer & order');
insert into sys_role values ('SITE',        'Site Team',         'Daily progress & timesheet');

-- Jenis dokumen + aturan approval (Blueprint 6.1; limit final lewat kebijakan, D-11)
insert into sys_doc_type (doc_type, doc_name, prefix, approver1_role, approver2_role, level2_limit)
values ('JO',  'Printing Job Order',       'JO',  'PRINT_MGR',   null,       0);
insert into sys_doc_type (doc_type, doc_name, prefix, approver1_role, approver2_role, level2_limit)
values ('PRJ', 'Project Budget',           'PJ',  'ENG_MGR',     'DIRECTOR', 100000000);
insert into sys_doc_type (doc_type, doc_name, prefix, approver1_role, approver2_role, level2_limit)
values ('PR',  'Purchase Requisition',     'PR',  'PROCUREMENT', 'DIRECTOR', 50000000);
insert into sys_doc_type (doc_type, doc_name, prefix, approver1_role, approver2_role, level2_limit)
values ('GR',  'Goods Receipt',            'GR',  null, null, 0);
insert into sys_doc_type (doc_type, doc_name, prefix, approver1_role, approver2_role, level2_limit)
values ('MI',  'Material Issue',           'MI',  null, null, 0);
insert into sys_doc_type (doc_type, doc_name, prefix, approver1_role, approver2_role, level2_limit)
values ('MR',  'Material Return',          'MR',  null, null, 0);
insert into sys_doc_type (doc_type, doc_name, prefix, approver1_role, approver2_role, level2_limit)
values ('ADJ', 'Stock Adjustment',         'ADJ', null, null, 0);

-- Business units (D-01) --------------------------------------------------------
insert into mdm_business_unit (bu_code, bu_name) values ('PRT', 'Printing');
insert into mdm_business_unit (bu_code, bu_name) values ('ENG', 'Engineering');

-- Gudang per BU (D-04) ---------------------------------------------------------
insert into mdm_warehouse (wh_code, wh_name, bu_id, location_type)
select 'WH-PRINT', 'Gudang Printing', bu_id, 'MAIN' from mdm_business_unit where bu_code = 'PRT';
insert into mdm_warehouse (wh_code, wh_name, bu_id, location_type)
select 'WH-PRINT-SUB01', 'Lokasi Vendor Laminasi (dummy)', bu_id, 'VENDOR' from mdm_business_unit where bu_code = 'PRT';
insert into mdm_warehouse (wh_code, wh_name, bu_id, location_type)
select 'WH-ENG', 'Gudang Engineering', bu_id, 'MAIN' from mdm_business_unit where bu_code = 'ENG';
insert into mdm_warehouse (wh_code, wh_name, bu_id, location_type)
select 'WH-ENG-SITE01', 'Site Proyek Conveyor (dummy)', bu_id, 'SITE' from mdm_business_unit where bu_code = 'ENG';

-- Customers & vendors (dummy) --------------------------------------------------
insert into mdm_customer (customer_code, customer_name, npwp, city, contact_person, phone, email, payment_term_days)
values ('C-0001', 'PT Contoh Retail Nusantara', '00.000.000.0-000.001', 'Jakarta', 'Budi', '021-0000001', 'budi@example.com', 30);
insert into mdm_customer (customer_code, customer_name, npwp, city, contact_person, phone, email, payment_term_days)
values ('C-0002', 'PT Contoh Pangan Makmur', '00.000.000.0-000.002', 'Bekasi', 'Sari', '021-0000002', 'sari@example.com', 45);
insert into mdm_customer (customer_code, customer_name, npwp, city, contact_person, phone, email, payment_term_days)
values ('C-0003', 'PT Contoh Logistik Andal', '00.000.000.0-000.003', 'Karawang', 'Andi', '0267-000003', 'andi@example.com', 30);

insert into mdm_vendor (vendor_code, vendor_name, vendor_type, city, phone)
values ('V-0001', 'CV Contoh Kertas Jaya', 'GOODS', 'Jakarta', '021-1000001');
insert into mdm_vendor (vendor_code, vendor_name, vendor_type, city, phone)
values ('V-0002', 'UD Contoh Laminasi', 'SUBCON', 'Tangerang', '021-1000002');
insert into mdm_vendor (vendor_code, vendor_name, vendor_type, city, phone)
values ('V-0003', 'PT Contoh Baja Perkasa', 'GOODS', 'Cilegon', '0254-100003');
insert into mdm_vendor (vendor_code, vendor_name, vendor_type, city, phone)
values ('V-0004', 'CV Contoh Instalasi Teknik', 'SUBCON', 'Bekasi', '021-1000004');

-- Items (dummy) ----------------------------------------------------------------
insert into mdm_item (item_code, item_name, item_category, uom, bu_id, min_stock, std_cost)
select 'PRT-PAP-AP150', 'Kertas Art Paper 150gsm 65x100', 'RAW', 'LEMBAR', bu_id, 5000, 1600 from mdm_business_unit where bu_code = 'PRT';
insert into mdm_item (item_code, item_name, item_category, uom, bu_id, min_stock, std_cost)
select 'PRT-INK-CMYK', 'Tinta Offset CMYK', 'RAW', 'KG', bu_id, 20, 120000 from mdm_business_unit where bu_code = 'PRT';
insert into mdm_item (item_code, item_name, item_category, uom, bu_id, min_stock, std_cost)
select 'PRT-PLT-CTP', 'Plat CTP 72x103', 'PLATE', 'LEMBAR', bu_id, 50, 100000 from mdm_business_unit where bu_code = 'PRT';
insert into mdm_item (item_code, item_name, item_category, uom, bu_id, min_stock, std_cost)
select 'ENG-STL-UNP100', 'Besi UNP 100', 'RAW', 'BTG', bu_id, 20, 650000 from mdm_business_unit where bu_code = 'ENG';
insert into mdm_item (item_code, item_name, item_category, uom, bu_id, min_stock, std_cost)
select 'ENG-STL-PLT6', 'Plat Baja 6mm 4x8', 'RAW', 'LBR', bu_id, 10, 2100000 from mdm_business_unit where bu_code = 'ENG';
insert into mdm_item (item_code, item_name, item_category, uom, bu_id, min_stock, std_cost)
select 'ENG-CON-ELD', 'Elektroda Las RB26 2.6mm', 'CONSUMABLE', 'KG', bu_id, 25, 45000 from mdm_business_unit where bu_code = 'ENG';
insert into mdm_item (item_code, item_name, item_category, uom, bu_id, min_stock, std_cost)
select 'ENG-CBL-NYY4', 'Kabel NYY 4x4mm', 'RAW', 'M', bu_id, 100, 55000 from mdm_business_unit where bu_code = 'ENG';

-- Contoh transaksi (dummy) -----------------------------------------------------
declare
   l_prt   number;
   l_eng   number;
   l_job   number;
   l_prj   number;
   l_wbs2  number;
   l_pr    number;
   function wh (p_code varchar2) return number is
      l_id number;
   begin
      select warehouse_id into l_id from mdm_warehouse where wh_code = p_code;
      return l_id;
   end;
   function itm (p_code varchar2) return number is
      l_id number;
   begin
      select item_id into l_id from mdm_item where item_code = p_code;
      return l_id;
   end;
   function cust (p_code varchar2) return number is
      l_id number;
   begin
      select customer_id into l_id from mdm_customer where customer_code = p_code;
      return l_id;
   end;
begin
   select bu_id into l_prt from mdm_business_unit where bu_code = 'PRT';
   select bu_id into l_eng from mdm_business_unit where bu_code = 'ENG';

   -- Penerimaan stok awal
   insert into inv_stock_txn (txn_type, warehouse_id, item_id, qty, unit_cost, reference)
   values ('RECEIPT', wh('WH-PRINT'), itm('PRT-PAP-AP150'), 20000, 1600, 'Saldo awal (dummy)');
   insert into inv_stock_txn (txn_type, warehouse_id, item_id, qty, unit_cost, reference)
   values ('RECEIPT', wh('WH-PRINT'), itm('PRT-INK-CMYK'), 50, 120000, 'Saldo awal (dummy)');
   insert into inv_stock_txn (txn_type, warehouse_id, item_id, qty, unit_cost, reference)
   values ('RECEIPT', wh('WH-PRINT'), itm('PRT-PLT-CTP'), 100, 100000, 'Saldo awal (dummy)');
   insert into inv_stock_txn (txn_type, warehouse_id, item_id, qty, unit_cost, reference)
   values ('RECEIPT', wh('WH-ENG'), itm('ENG-STL-UNP100'), 60, 650000, 'Saldo awal (dummy)');
   insert into inv_stock_txn (txn_type, warehouse_id, item_id, qty, unit_cost, reference)
   values ('RECEIPT', wh('WH-ENG'), itm('ENG-STL-PLT6'), 15, 2100000, 'Saldo awal (dummy)');
   insert into inv_stock_txn (txn_type, warehouse_id, item_id, qty, unit_cost, reference)
   values ('RECEIPT', wh('WH-ENG'), itm('ENG-CON-ELD'), 80, 45000, 'Saldo awal (dummy)');

   -- Job order contoh 10.000 brosur (Blueprint 3.3), langsung APPROVED untuk demo
   mbms_approval.set_bypass(true);
   insert into prt_job_order (bu_id, customer_id, job_type, product_desc, qty_order, ups_per_sheet, insheet_pct,
                              due_date, selling_price, est_paper, est_ink, est_plate, est_machine, est_finishing,
                              est_labor, est_overhead, status)
   values (l_prt, cust('C-0001'), 'MTO', 'Brosur A4 4/4 Art Paper 150gsm, laminasi doff', 10000, 4, 5,
           trunc(sysdate) + 14, 19500000, 8000000, 1200000, 800000, 2000000, 1500000, 500000, 1000000, 'APPROVED')
   returning job_id into l_job;

   insert into prt_job_order (bu_id, customer_id, job_type, product_desc, qty_order, ups_per_sheet, insheet_pct,
                              due_date, selling_price, est_paper, est_ink, est_plate, est_machine, est_finishing,
                              est_labor, est_overhead)
   values (l_prt, cust('C-0002'), 'MTO', 'Kemasan karton lipat 3 warna', 5000, 2, 7,
           trunc(sysdate) + 21, 14000000, 6000000, 900000, 600000, 1800000, 1200000, 400000, 800000);

   -- Proyek conveyor contoh (Blueprint 4.4), langsung APPROVED untuk demo
   insert into prj_project (bu_id, customer_id, project_name, project_type, contract_value, retention_pct,
                            start_date, end_date, progress_pct, project_manager, status)
   values (l_eng, cust('C-0003'), 'Conveyor System Gudang Karawang', 'FABRICATION', 230000000, 5,
           trunc(sysdate) - 30, trunc(sysdate) + 60, 25, 'PM.DUMMY', 'APPROVED')
   returning project_id into l_prj;

   insert into prj_wbs (project_id, wbs_code, wbs_name, cost_category, budget_amount) values (l_prj, '1.0', 'Engineering & Design', 'LABOR', 15000000);
   insert into prj_wbs (project_id, wbs_code, wbs_name, cost_category, budget_amount) values (l_prj, '2.0', 'Procurement Material', 'MATERIAL', 80000000) returning wbs_id into l_wbs2;
   insert into prj_wbs (project_id, wbs_code, wbs_name, cost_category, budget_amount) values (l_prj, '3.0', 'Workshop Fabrication', 'LABOR', 40000000);
   insert into prj_wbs (project_id, wbs_code, wbs_name, cost_category, budget_amount) values (l_prj, '4.0', 'Surface Treatment', 'SUBCON', 10000000);
   insert into prj_wbs (project_id, wbs_code, wbs_name, cost_category, budget_amount) values (l_prj, '5.0', 'Site Installation', 'SUBCON', 30000000);
   insert into prj_wbs (project_id, wbs_code, wbs_name, cost_category, budget_amount) values (l_prj, '6.0', 'Testing & Commissioning', 'OTHER', 10000000);
   mbms_approval.set_bypass(false);

   -- Material issue ke job dan proyek
   insert into inv_stock_txn (txn_type, warehouse_id, item_id, qty, job_id, reference)
   values ('ISSUE', wh('WH-PRINT'), itm('PRT-PAP-AP150'), 2650, l_job, 'Issue kertas + insheet 5%');
   insert into inv_stock_txn (txn_type, warehouse_id, item_id, qty, job_id, reference)
   values ('ISSUE', wh('WH-PRINT'), itm('PRT-INK-CMYK'), 8, l_job, 'Issue tinta');
   insert into inv_stock_txn (txn_type, warehouse_id, item_id, qty, project_id, wbs_id, reference)
   values ('ISSUE', wh('WH-ENG'), itm('ENG-STL-UNP100'), 40, l_prj, l_wbs2, 'Frame conveyor');
   insert into inv_stock_txn (txn_type, warehouse_id, item_id, qty, project_id, wbs_id, reference)
   values ('ISSUE', wh('WH-ENG'), itm('ENG-STL-PLT6'), 8, l_prj, l_wbs2, 'Plat dudukan');

   -- PR draft untuk proyek
   insert into pur_requisition (bu_id, purpose, project_id, wbs_id, need_date, description)
   values (l_eng, 'PROJECT', l_prj, l_wbs2, trunc(sysdate) + 7, 'Tambahan material frame conveyor')
   returning pr_id into l_pr;
   insert into pur_requisition_line (pr_id, item_id, qty, unit_price) values (l_pr, itm('ENG-STL-UNP100'), 10, 650000);
   insert into pur_requisition_line (pr_id, item_id, qty, unit_price) values (l_pr, itm('ENG-CON-ELD'), 20, 45000);
end;
/

commit;

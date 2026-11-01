-- =============================================================================
-- MBMS MVP - Deinstall (HANYA untuk sandbox; menghapus semua objek dan data MBMS)
-- =============================================================================
drop view sys_approval_v;
drop view prj_project_summary_v;
drop view prj_wbs_budget_v;
drop view prt_job_cost_v;
drop view inv_stock_on_hand_v;
drop view inv_stock_txn_v;
drop view pur_requisition_line_v;
drop view pur_requisition_v;
drop table inv_stock_txn purge;
drop table pur_requisition_line purge;
drop table pur_requisition purge;
drop table prj_wbs purge;
drop table prj_project purge;
drop table prt_job_order purge;
drop table mdm_warehouse purge;
drop table mdm_item purge;
drop table mdm_vendor purge;
drop table mdm_customer purge;
drop table mdm_business_unit purge;
drop table sys_approval purge;
drop table sys_doc_seq purge;
drop table sys_doc_type purge;
drop table sys_user_role purge;
drop table sys_role purge;
drop package mbms_approval;
drop package mbms_inv;
drop package mbms_doc;
drop package mbms_sec;

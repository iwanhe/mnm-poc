-- =============================================================================
-- MBMS MVP - 04 Views (reporting & costing)
-- =============================================================================

create or replace view pur_requisition_v as
select r.pr_id
     , r.pr_no
     , r.bu_id
     , bu.bu_code
     , r.pr_date
     , r.purpose
     , r.job_id
     , j.job_no
     , r.project_id
     , p.project_no
     , r.wbs_id
     , w.wbs_code
     , r.requested_by
     , r.need_date
     , r.description
     , (select nvl(sum(l.line_amount),0) from pur_requisition_line l where l.pr_id = r.pr_id) total_amount
     , (select count(*) from pur_requisition_line l where l.pr_id = r.pr_id) line_count
     , r.status
     , r.created_on
  from pur_requisition r
  join mdm_business_unit bu on bu.bu_id = r.bu_id
  left join prt_job_order j on j.job_id = r.job_id
  left join prj_project p on p.project_id = r.project_id
  left join prj_wbs w on w.wbs_id = r.wbs_id;

create or replace view pur_requisition_line_v as
select l.line_id
     , l.pr_id
     , r.pr_no
     , r.status pr_status
     , l.line_no
     , l.item_id
     , i.item_code
     , i.item_name
     , i.uom
     , l.qty
     , l.unit_price
     , l.line_amount
     , l.notes
  from pur_requisition_line l
  join pur_requisition r on r.pr_id = l.pr_id
  join mdm_item i on i.item_id = l.item_id;

create or replace view inv_stock_txn_v as
select t.txn_id
     , t.txn_no
     , t.txn_date
     , t.txn_type
     , bu.bu_code
     , w.wh_code
     , w.wh_name
     , i.item_code
     , i.item_name
     , i.uom
     , t.qty
     , t.qty_signed
     , t.unit_cost
     , t.total_cost
     , j.job_no
     , p.project_no
     , wb.wbs_code
     , t.reference
     , t.notes
     , t.created_by
     , t.created_on
  from inv_stock_txn t
  join mdm_business_unit bu on bu.bu_id = t.bu_id
  join mdm_warehouse w on w.warehouse_id = t.warehouse_id
  join mdm_item i on i.item_id = t.item_id
  left join prt_job_order j on j.job_id = t.job_id
  left join prj_project p on p.project_id = t.project_id
  left join prj_wbs wb on wb.wbs_id = t.wbs_id;

-- Posisi stok per item per gudang/lokasi
create or replace view inv_stock_on_hand_v as
select bu.bu_code
     , w.warehouse_id
     , w.wh_code
     , w.wh_name
     , w.location_type
     , i.item_id
     , i.item_code
     , i.item_name
     , i.item_category
     , i.uom
     , i.min_stock
     , s.qty_on_hand
     , mbms_inv.avg_cost(i.item_id) avg_cost
     , round(s.qty_on_hand * mbms_inv.avg_cost(i.item_id), 2) stock_value
     , case when s.qty_on_hand < i.min_stock then 'Y' else 'N' end below_min_yn
  from (select item_id, warehouse_id, sum(qty_signed) qty_on_hand
          from inv_stock_txn
         group by item_id, warehouse_id) s
  join mdm_item i on i.item_id = s.item_id
  join mdm_warehouse w on w.warehouse_id = s.warehouse_id
  join mdm_business_unit bu on bu.bu_id = w.bu_id;

-- Actual costing per job (D-07): estimasi vs aktual
create or replace view prt_job_cost_v as
select j.job_id
     , j.job_no
     , j.job_type
     , c.customer_name
     , j.product_desc
     , j.status
     , j.due_date
     , j.qty_order
     , j.qty_produced
     , j.qty_reject
     , j.qty_delivered
     , j.insheet_pct
     , case when j.qty_produced + j.qty_reject > 0
            then round(100 * j.qty_reject / (j.qty_produced + j.qty_reject), 2) end waste_pct
     , j.selling_price
     , j.est_hpp
     , nvl(m.act_material, 0) act_material
     , j.act_other_cost
     , nvl(m.act_material, 0) + j.act_other_cost act_hpp
     , j.est_hpp - (nvl(m.act_material, 0) + j.act_other_cost) hpp_variance
     , j.selling_price - j.est_hpp est_gross_profit
     , j.selling_price - (nvl(m.act_material, 0) + j.act_other_cost) act_gross_profit
     , case when j.selling_price > 0
            then round(100 * (j.selling_price - (nvl(m.act_material, 0) + j.act_other_cost)) / j.selling_price, 2) end act_margin_pct
  from prt_job_order j
  left join mdm_customer c on c.customer_id = j.customer_id
  left join (select job_id, -sum(qty_signed * nvl(unit_cost,0)) act_material
               from inv_stock_txn
              where job_id is not null
                and txn_type in ('ISSUE','RETURN')
              group by job_id) m on m.job_id = j.job_id;

-- Budget vs actual per WBS (Blueprint 4.4)
create or replace view prj_wbs_budget_v as
select p.project_id
     , p.project_no
     , p.project_name
     , p.status project_status
     , w.wbs_id
     , w.wbs_code
     , w.wbs_name
     , w.cost_category
     , w.budget_amount
     , nvl(a.actual_amount, 0) actual_amount
     , nvl(c.committed_amount, 0) committed_amount
     , w.budget_amount - nvl(a.actual_amount, 0) variance_amount
     , w.budget_amount - nvl(a.actual_amount, 0) - nvl(c.committed_amount, 0) remaining_amount
     , case when w.budget_amount > 0
            then round(100 * (nvl(a.actual_amount, 0) + nvl(c.committed_amount, 0)) / w.budget_amount, 1) end used_pct
  from prj_wbs w
  join prj_project p on p.project_id = w.project_id
  left join (select wbs_id, -sum(qty_signed * nvl(unit_cost,0)) actual_amount
               from inv_stock_txn
              where wbs_id is not null
                and txn_type in ('ISSUE','RETURN')
              group by wbs_id) a on a.wbs_id = w.wbs_id
  left join (select r.wbs_id, sum(l.line_amount) committed_amount
               from pur_requisition r
               join pur_requisition_line l on l.pr_id = r.pr_id
              where r.wbs_id is not null
                and r.status in ('SUBMITTED','APPROVED')
              group by r.wbs_id) c on c.wbs_id = w.wbs_id;

-- Ringkasan proyek: kontrak, budget, aktual, margin
create or replace view prj_project_summary_v as
select p.project_id
     , p.project_no
     , p.project_name
     , p.project_type
     , c.customer_name
     , p.status
     , p.start_date
     , p.end_date
     , p.progress_pct
     , p.contract_value
     , p.retention_pct
     , round(p.contract_value * p.retention_pct / 100, 2) retention_amount
     , nvl(b.budget_amount, 0) budget_amount
     , nvl(a.actual_amount, 0) actual_amount
     , nvl(b.budget_amount, 0) - nvl(a.actual_amount, 0) cost_variance
     , p.contract_value - nvl(b.budget_amount, 0) planned_margin
     , case when nvl(b.budget_amount, 0) > p.contract_value then 'Y' else 'N' end loss_warning_yn
     , case when p.end_date < trunc(sysdate) and p.status not in ('COMPLETED','CLOSED','CANCELLED') then 'Y' else 'N' end overdue_yn
  from prj_project p
  join mdm_customer c on c.customer_id = p.customer_id
  left join (select project_id, sum(budget_amount) budget_amount from prj_wbs group by project_id) b
         on b.project_id = p.project_id
  left join (select project_id, -sum(qty_signed * nvl(unit_cost,0)) actual_amount
               from inv_stock_txn
              where project_id is not null
                and txn_type in ('ISSUE','RETURN')
              group by project_id) a on a.project_id = p.project_id;

create or replace view sys_approval_v as
select a.approval_id
     , a.doc_type
     , d.doc_name
     , a.doc_id
     , a.doc_no
     , bu.bu_code
     , a.approval_level
     , a.approver_role
     , a.amount
     , a.requested_by
     , a.requested_on
     , a.status
     , a.acted_by
     , a.acted_on
     , a.note
     , mbms_approval.can_act_yn(a.approval_id) can_act_yn
  from sys_approval a
  join sys_doc_type d on d.doc_type = a.doc_type
  left join mdm_business_unit bu on bu.bu_id = a.bu_id;

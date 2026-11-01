-- =============================================================================
-- MBMS MVP - 03 Triggers
-- Audit kolom, penomoran dokumen, dan guard business rule (BR-02, BR-05, BR-07)
-- =============================================================================

-- Audit-only triggers untuk master data --------------------------------------
create or replace trigger sys_user_role_biu
before insert or update on sys_user_role for each row
begin
   :new.username := upper(:new.username);
   if inserting then
      :new.created_by := mbms_sec.app_user;
      :new.created_on := sysdate;
   end if;
   :new.updated_by := mbms_sec.app_user;
   :new.updated_on := sysdate;
end;
/

create or replace trigger mdm_business_unit_biu
before insert or update on mdm_business_unit for each row
begin
   :new.bu_code := upper(:new.bu_code);
   if inserting then
      :new.created_by := mbms_sec.app_user;
      :new.created_on := sysdate;
   end if;
   :new.updated_by := mbms_sec.app_user;
   :new.updated_on := sysdate;
end;
/

create or replace trigger mdm_customer_biu
before insert or update on mdm_customer for each row
begin
   :new.customer_code := upper(:new.customer_code);
   if inserting then
      :new.created_by := mbms_sec.app_user;
      :new.created_on := sysdate;
   end if;
   :new.updated_by := mbms_sec.app_user;
   :new.updated_on := sysdate;
end;
/

create or replace trigger mdm_vendor_biu
before insert or update on mdm_vendor for each row
begin
   :new.vendor_code := upper(:new.vendor_code);
   if inserting then
      :new.created_by := mbms_sec.app_user;
      :new.created_on := sysdate;
   end if;
   :new.updated_by := mbms_sec.app_user;
   :new.updated_on := sysdate;
end;
/

create or replace trigger mdm_item_biu
before insert or update on mdm_item for each row
begin
   :new.item_code := upper(:new.item_code);
   if inserting then
      :new.created_by := mbms_sec.app_user;
      :new.created_on := sysdate;
   end if;
   :new.updated_by := mbms_sec.app_user;
   :new.updated_on := sysdate;
end;
/

create or replace trigger mdm_warehouse_biu
before insert or update on mdm_warehouse for each row
begin
   :new.wh_code := upper(:new.wh_code);
   if inserting then
      :new.created_by := mbms_sec.app_user;
      :new.created_on := sysdate;
   end if;
   :new.updated_by := mbms_sec.app_user;
   :new.updated_on := sysdate;
end;
/

-- Printing Job Order -----------------------------------------------------------
create or replace trigger prt_job_order_biu
before insert or update on prt_job_order for each row
begin
   if inserting then
      if not mbms_approval.bypass then
         :new.status := 'DRAFT';
      end if;
      if :new.job_no is null then
         :new.job_no := mbms_doc.next_no('JO', :new.bu_id, sysdate);
      end if;
      :new.created_by := mbms_sec.app_user;
      :new.created_on := sysdate;
   else
      if not mbms_approval.bypass then
         if :old.status = 'SUBMITTED' then
            raise_application_error(-20201, 'Job order ' || :old.job_no || ' sedang menunggu approval dan tidak dapat diubah.');
         end if;
         if :old.status in ('CLOSED','CANCELLED') then
            raise_application_error(-20202, 'Job order ' || :old.job_no || ' sudah ' || :old.status || '.');
         end if;
         -- status operasional hanya setelah approval (Blueprint 6.3 khusus Printing)
         if :new.status <> :old.status
            and not (:old.status in ('APPROVED','IN_PROGRESS','COMPLETED')
                     and :new.status in ('IN_PROGRESS','COMPLETED','CLOSED'))
         then
            raise_application_error(-20203, 'Perubahan status ' || :old.status || ' -> ' || :new.status
               || ' tidak diizinkan. Gunakan Submit for Approval.');
         end if;
         -- spesifikasi & estimasi terkunci setelah approval (BR-09)
         if :old.status in ('APPROVED','IN_PROGRESS','COMPLETED') then
            :new.customer_id   := :old.customer_id;
            :new.product_desc  := :old.product_desc;
            :new.qty_order     := :old.qty_order;
            :new.selling_price := :old.selling_price;
            :new.est_paper     := :old.est_paper;
            :new.est_ink       := :old.est_ink;
            :new.est_plate     := :old.est_plate;
            :new.est_machine   := :old.est_machine;
            :new.est_finishing := :old.est_finishing;
            :new.est_labor     := :old.est_labor;
            :new.est_overhead  := :old.est_overhead;
         end if;
      end if;
   end if;
   :new.updated_by := mbms_sec.app_user;
   :new.updated_on := sysdate;
end;
/

-- Engineering Project ----------------------------------------------------------
create or replace trigger prj_project_biu
before insert or update on prj_project for each row
begin
   if inserting then
      if not mbms_approval.bypass then
         :new.status := 'DRAFT';
      end if;
      if :new.project_no is null then
         :new.project_no := mbms_doc.next_no('PRJ', :new.bu_id, sysdate);
      end if;
      :new.created_by := mbms_sec.app_user;
      :new.created_on := sysdate;
   else
      if not mbms_approval.bypass then
         if :old.status = 'SUBMITTED' then
            raise_application_error(-20211, 'Proyek ' || :old.project_no || ' sedang menunggu approval budget dan tidak dapat diubah.');
         end if;
         if :old.status in ('CLOSED','CANCELLED') then
            raise_application_error(-20212, 'Proyek ' || :old.project_no || ' sudah ' || :old.status || '.');
         end if;
         if :new.status <> :old.status
            and not (:old.status in ('APPROVED','IN_PROGRESS','COMPLETED')
                     and :new.status in ('IN_PROGRESS','COMPLETED','CLOSED'))
         then
            raise_application_error(-20213, 'Perubahan status ' || :old.status || ' -> ' || :new.status
               || ' tidak diizinkan. Gunakan Submit for Approval.');
         end if;
         -- nilai kontrak hanya berubah lewat change order (Fase 3)
         if :old.status in ('APPROVED','IN_PROGRESS','COMPLETED') then
            :new.contract_value := :old.contract_value;
            :new.customer_id    := :old.customer_id;
         end if;
      end if;
   end if;
   :new.updated_by := mbms_sec.app_user;
   :new.updated_on := sysdate;
end;
/

create or replace trigger prj_wbs_biu
before insert or update or delete on prj_wbs for each row
declare
   l_status prj_project.status%type;
   e_mutating exception;
   pragma exception_init(e_mutating, -4091);
begin
   begin
      select status into l_status
        from prj_project
       where project_id = coalesce(:new.project_id, :old.project_id);
   exception
      when e_mutating then
         return;  -- delete cascade dari prj_project (hanya proyek DRAFT yang bisa dihapus)
   end;

   -- budget yang sudah disetujui hanya berubah lewat revisi/change order (BR-09)
   if not mbms_approval.bypass and l_status not in ('DRAFT','REJECTED') then
      raise_application_error(-20221, 'Budget WBS terkunci karena proyek berstatus ' || l_status || '.');
   end if;

   if deleting then
      return;
   end if;
   if inserting then
      :new.created_by := mbms_sec.app_user;
      :new.created_on := sysdate;
   end if;
   :new.updated_by := mbms_sec.app_user;
   :new.updated_on := sysdate;
end;
/

-- Purchase Requisition ---------------------------------------------------------
create or replace trigger pur_requisition_biu
before insert or update on pur_requisition for each row
begin
   if :new.purpose <> 'JOB' then
      :new.job_id := null;
   end if;
   if :new.purpose <> 'PROJECT' then
      :new.project_id := null;
      :new.wbs_id     := null;
   end if;

   if inserting then
      if not mbms_approval.bypass then
         :new.status := 'DRAFT';
      end if;
      if :new.pr_no is null then
         :new.pr_no := mbms_doc.next_no('PR', :new.bu_id, :new.pr_date);
      end if;
      :new.requested_by := nvl(:new.requested_by, mbms_sec.app_user);
      :new.created_by   := mbms_sec.app_user;
      :new.created_on   := sysdate;
   elsif not mbms_approval.bypass then
      if :old.status not in ('DRAFT','REJECTED') then
         raise_application_error(-20231, 'PR ' || :old.pr_no || ' berstatus ' || :old.status || ' dan tidak dapat diubah.');
      end if;
      if :new.status <> :old.status and :new.status <> 'CANCELLED' then
         raise_application_error(-20232, 'Status PR hanya berubah lewat approval.');
      end if;
   end if;
   :new.updated_by := mbms_sec.app_user;
   :new.updated_on := sysdate;
end;
/

create or replace trigger pur_requisition_line_biud
before insert or update or delete on pur_requisition_line for each row
declare
   l_status pur_requisition.status%type;
   e_mutating exception;
   pragma exception_init(e_mutating, -4091);
begin
   begin
      select status into l_status from pur_requisition where pr_id = coalesce(:new.pr_id, :old.pr_id);
   exception
      when e_mutating then
         return;  -- delete cascade dari pur_requisition
   end;
   if not mbms_approval.bypass and l_status not in ('DRAFT','REJECTED') then
      raise_application_error(-20241, 'Baris PR tidak dapat diubah karena PR berstatus ' || l_status || '.');
   end if;
   if not deleting then
      if inserting then
         if :new.line_no is null then
            select nvl(max(line_no),0) + 10 into :new.line_no
              from pur_requisition_line where pr_id = :new.pr_id;
         end if;
         :new.created_by := mbms_sec.app_user;
         :new.created_on := sysdate;
      end if;
      :new.updated_by := mbms_sec.app_user;
      :new.updated_on := sysdate;
   end if;
end;
/

-- Stock ledger -----------------------------------------------------------------
create or replace trigger inv_stock_txn_bi
before insert on inv_stock_txn for each row
declare
   l_on_hand number;
   l_status  varchar2(20);
begin
   select bu_id into :new.bu_id from mdm_warehouse where warehouse_id = :new.warehouse_id;
   :new.qty_signed := :new.qty * mbms_inv.sign_of(:new.txn_type);

   -- WBS harus milik proyek yang sama
   if :new.wbs_id is not null then
      select project_id into :new.project_id from prj_wbs where wbs_id = :new.wbs_id;
   end if;

   -- material hanya di-issue ke job/proyek yang sudah disetujui (Blueprint 6.3)
   if :new.txn_type in ('ISSUE','RETURN') then
      if :new.job_id is null and :new.project_id is null then
         raise_application_error(-20250, 'Issue/return material wajib mereferensikan Job Order atau Proyek (BR-05).');
      elsif :new.job_id is not null then
         select status into l_status from prt_job_order where job_id = :new.job_id;
      else
         select status into l_status from prj_project where project_id = :new.project_id;
      end if;
      if l_status not in ('APPROVED','IN_PROGRESS','COMPLETED') then
         raise_application_error(-20251, 'Material hanya dapat di-issue ke job/proyek yang sudah disetujui (status saat ini: ' || l_status || ').');
      end if;
   end if;

   -- transaksi keluar: biaya = rata-rata, stok tidak boleh minus (BR-07)
   if :new.qty_signed < 0 then
      if :new.unit_cost is null then
         :new.unit_cost := mbms_inv.avg_cost(:new.item_id);
      end if;
      l_on_hand := mbms_inv.on_hand(:new.item_id, :new.warehouse_id);
      if l_on_hand < :new.qty then
         raise_application_error(-20252, 'Stok tidak cukup. On hand: ' || l_on_hand || ', diminta: ' || :new.qty);
      end if;
   elsif :new.txn_type = 'RETURN' and :new.unit_cost is null then
      :new.unit_cost := mbms_inv.avg_cost(:new.item_id);
   end if;

   if :new.txn_no is null then
      :new.txn_no := mbms_doc.next_no(
         case :new.txn_type when 'RECEIPT' then 'GR' when 'ISSUE' then 'MI' when 'RETURN' then 'MR' else 'ADJ' end,
         :new.bu_id, :new.txn_date);
   end if;
   :new.created_by := mbms_sec.app_user;
   :new.created_on := sysdate;
end;
/

-- Transaksi stok yang sudah diposting tidak dihapus/diubah (Blueprint 6.1: reversal transaction)
create or replace trigger inv_stock_txn_bud
before update or delete on inv_stock_txn for each row
begin
   if not mbms_approval.bypass then
      raise_application_error(-20253, 'Transaksi stok yang sudah diposting tidak dapat diubah atau dihapus. Buat transaksi koreksi (ADJ_IN/ADJ_OUT/RETURN).');
   end if;
end;
/

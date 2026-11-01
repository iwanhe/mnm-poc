-- =============================================================================
-- MBMS MVP - 02 PL/SQL packages
-- Semua logika bisnis di package, bukan di halaman APEX (Blueprint 7.1)
-- =============================================================================

-- -----------------------------------------------------------------------------
-- MBMS_SEC : role-based access (Blueprint 6.2)
-- -----------------------------------------------------------------------------
create or replace package mbms_sec as
   function app_user return varchar2;
   -- TRUE bila user memiliki role, atau role ADMIN.
   -- Mode bootstrap: selama belum ada satu pun user ADMIN, semua user dianggap ADMIN
   -- supaya admin pertama bisa mendaftarkan dirinya di halaman Users & Roles.
   function has_role (p_role in varchar2, p_username in varchar2 default null) return boolean;
   function has_role_yn (p_role in varchar2, p_username in varchar2 default null) return varchar2;
   function bootstrap_mode return boolean;
end mbms_sec;
/

create or replace package body mbms_sec as

   function app_user return varchar2 is
   begin
      return coalesce(sys_context('APEX$SESSION','APP_USER'), sys_context('USERENV','SESSION_USER'));
   end app_user;

   function bootstrap_mode return boolean is
      l_cnt number;
   begin
      select count(*) into l_cnt from sys_user_role where role_code = 'ADMIN';
      return l_cnt = 0;
   end bootstrap_mode;

   function has_role (p_role in varchar2, p_username in varchar2 default null) return boolean is
      l_user varchar2(255) := upper(coalesce(p_username, app_user));
      l_cnt  number;
   begin
      if bootstrap_mode then
         return true;
      end if;
      select count(*)
        into l_cnt
        from sys_user_role
       where upper(username) = l_user
         and role_code in (upper(p_role), 'ADMIN');
      return l_cnt > 0;
   end has_role;

   function has_role_yn (p_role in varchar2, p_username in varchar2 default null) return varchar2 is
   begin
      return case when has_role(p_role, p_username) then 'Y' else 'N' end;
   end has_role_yn;

end mbms_sec;
/

-- -----------------------------------------------------------------------------
-- MBMS_DOC : penomoran dokumen configurable (Blueprint 6.4, D-11)
-- Format: <PREFIX>-<BU>-<YYYY>-<NNNN>, contoh JO-PRT-2026-0001
-- -----------------------------------------------------------------------------
create or replace package mbms_doc as
   function next_no (p_doc_type in varchar2, p_bu_id in number, p_date in date default sysdate) return varchar2;
end mbms_doc;
/

create or replace package body mbms_doc as

   function next_no (p_doc_type in varchar2, p_bu_id in number, p_date in date default sysdate) return varchar2 is
      l_prefix  sys_doc_type.prefix%type;
      l_bu_code mdm_business_unit.bu_code%type := 'GEN';
      l_period  varchar2(4) := to_char(nvl(p_date, sysdate), 'YYYY');
      l_no      number;
   begin
      select prefix into l_prefix from sys_doc_type where doc_type = p_doc_type;

      if p_bu_id is not null then
         select bu_code into l_bu_code from mdm_business_unit where bu_id = p_bu_id;
      end if;

      merge into sys_doc_seq s
      using (select p_doc_type doc_type, l_bu_code bu_code, l_period period from dual) n
         on (s.doc_type = n.doc_type and s.bu_code = n.bu_code and s.period = n.period)
       when not matched then insert (doc_type, bu_code, period, last_no)
                             values (n.doc_type, n.bu_code, n.period, 0);

      update sys_doc_seq
         set last_no = last_no + 1
       where doc_type = p_doc_type
         and bu_code  = l_bu_code
         and period   = l_period
      returning last_no into l_no;

      return l_prefix || '-' || l_bu_code || '-' || l_period || '-' || lpad(l_no, 4, '0');
   end next_no;

end mbms_doc;
/

-- -----------------------------------------------------------------------------
-- MBMS_INV : stock ledger (Blueprint 5.3, BR-04, BR-07)
-- -----------------------------------------------------------------------------
create or replace package mbms_inv as
   function sign_of (p_txn_type in varchar2) return number;
   function on_hand (p_item_id in number, p_warehouse_id in number) return number;
   function avg_cost (p_item_id in number) return number;
end mbms_inv;
/

create or replace package body mbms_inv as

   function sign_of (p_txn_type in varchar2) return number is
   begin
      return case when p_txn_type in ('RECEIPT','RETURN','ADJ_IN') then 1 else -1 end;
   end sign_of;

   function on_hand (p_item_id in number, p_warehouse_id in number) return number is
      l_qty number;
   begin
      select nvl(sum(qty_signed), 0)
        into l_qty
        from inv_stock_txn
       where item_id = p_item_id
         and warehouse_id = p_warehouse_id;
      return l_qty;
   end on_hand;

   -- Moving average sederhana dari transaksi masuk; fallback ke standard cost
   function avg_cost (p_item_id in number) return number is
      l_cost number;
   begin
      select case when sum(qty) > 0 then round(sum(qty * nvl(unit_cost,0)) / sum(qty), 2) end
        into l_cost
        from inv_stock_txn
       where item_id = p_item_id
         and txn_type in ('RECEIPT','ADJ_IN');
      if l_cost is null then
         select std_cost into l_cost from mdm_item where item_id = p_item_id;
      end if;
      return l_cost;
   end avg_cost;

end mbms_inv;
/

-- -----------------------------------------------------------------------------
-- MBMS_APPROVAL : approval engine generik (Blueprint 6, BR-02, BR-03)
-- Dokumen: JO (Printing Job Order), PRJ (Project Budget), PR (Purchase Requisition)
-- Level 1 selalu; level 2 bila amount > sys_doc_type.level2_limit
-- Maker-checker: approver tidak boleh sama dengan requester.
-- -----------------------------------------------------------------------------
create or replace package mbms_approval as
   -- dipakai trigger untuk mengizinkan perubahan status hanya lewat package ini
   function bypass return boolean;
   procedure set_bypass (p_value in boolean);

   function doc_amount (p_doc_type in varchar2, p_doc_id in number) return number;
   procedure submit  (p_doc_type in varchar2, p_doc_id in number);
   procedure approve (p_approval_id in number, p_note in varchar2 default null);
   procedure reject  (p_approval_id in number, p_note in varchar2 default null);
   function can_act_yn (p_approval_id in number) return varchar2;
end mbms_approval;
/

create or replace package body mbms_approval as

   g_bypass boolean := false;

   function bypass return boolean is begin return g_bypass; end bypass;
   procedure set_bypass (p_value in boolean) is begin g_bypass := p_value; end set_bypass;

   procedure set_doc_status (p_doc_type in varchar2, p_doc_id in number, p_status in varchar2) is
   begin
      g_bypass := true;
      case p_doc_type
         when 'JO'  then update prt_job_order   set status = p_status where job_id     = p_doc_id;
         when 'PRJ' then update prj_project     set status = p_status where project_id = p_doc_id;
         when 'PR'  then update pur_requisition set status = p_status where pr_id      = p_doc_id;
      end case;
      g_bypass := false;
   exception
      when others then
         g_bypass := false;
         raise;
   end set_doc_status;

   function doc_amount (p_doc_type in varchar2, p_doc_id in number) return number is
      l_amt number;
   begin
      case p_doc_type
         when 'JO'  then select est_hpp into l_amt from prt_job_order where job_id = p_doc_id;
         when 'PRJ' then select nvl(sum(budget_amount),0) into l_amt from prj_wbs where project_id = p_doc_id;
         when 'PR'  then select nvl(sum(line_amount),0) into l_amt from pur_requisition_line where pr_id = p_doc_id;
      end case;
      return l_amt;
   end doc_amount;

   procedure get_doc (p_doc_type in varchar2, p_doc_id in number,
                      x_doc_no out varchar2, x_bu_id out number, x_status out varchar2) is
   begin
      case p_doc_type
         when 'JO'  then select job_no, bu_id, status into x_doc_no, x_bu_id, x_status from prt_job_order where job_id = p_doc_id;
         when 'PRJ' then select project_no, bu_id, status into x_doc_no, x_bu_id, x_status from prj_project where project_id = p_doc_id;
         when 'PR'  then select pr_no, bu_id, status into x_doc_no, x_bu_id, x_status from pur_requisition where pr_id = p_doc_id;
      end case;
   end get_doc;

   -- BR-03 budget control untuk PR proyek
   procedure check_pr_budget (p_pr_id in number) is
      l_project_id number;
      l_wbs_id     number;
      l_budget     number;
      l_used       number;
      l_committed  number;
      l_amount     number := doc_amount('PR', p_pr_id);
   begin
      select project_id, wbs_id into l_project_id, l_wbs_id from pur_requisition where pr_id = p_pr_id;
      if l_project_id is null then
         return;
      end if;

      select nvl(sum(budget_amount),0) into l_budget
        from prj_wbs
       where project_id = l_project_id
         and (l_wbs_id is null or wbs_id = l_wbs_id);

      select nvl(-sum(qty_signed * nvl(unit_cost,0)),0) into l_used
        from inv_stock_txn
       where project_id = l_project_id
         and (l_wbs_id is null or wbs_id = l_wbs_id)
         and txn_type in ('ISSUE','RETURN');

      select nvl(sum(l.line_amount),0) into l_committed
        from pur_requisition r
        join pur_requisition_line l on l.pr_id = r.pr_id
       where r.project_id = l_project_id
         and (l_wbs_id is null or r.wbs_id = l_wbs_id)
         and r.status in ('SUBMITTED','APPROVED')
         and r.pr_id <> p_pr_id;

      if l_amount > l_budget - l_used - l_committed then
         raise_application_error(-20101,
            'Anggaran tidak cukup. Sisa anggaran: ' || to_char(l_budget - l_used - l_committed, 'FM999G999G999G990')
            || ', nilai PR: ' || to_char(l_amount, 'FM999G999G999G990'));
      end if;
   end check_pr_budget;

   procedure create_step (p_doc_type in varchar2, p_doc_id in number, p_level in number,
                          p_role in varchar2, p_requested_by in varchar2) is
      l_doc_no varchar2(30);
      l_bu_id  number;
      l_status varchar2(20);
   begin
      get_doc(p_doc_type, p_doc_id, l_doc_no, l_bu_id, l_status);
      insert into sys_approval (doc_type, doc_id, doc_no, bu_id, approval_level, approver_role,
                                amount, requested_by, requested_on, status)
      values (p_doc_type, p_doc_id, l_doc_no, l_bu_id, p_level, p_role,
              doc_amount(p_doc_type, p_doc_id), p_requested_by, sysdate, 'PENDING');
   end create_step;

   procedure submit (p_doc_type in varchar2, p_doc_id in number) is
      l_doc_no varchar2(30);
      l_bu_id  number;
      l_status varchar2(20);
      l_cnt    number;
      l_type   sys_doc_type%rowtype;
   begin
      get_doc(p_doc_type, p_doc_id, l_doc_no, l_bu_id, l_status);
      if l_status not in ('DRAFT','REJECTED') then
         raise_application_error(-20102, 'Dokumen ' || l_doc_no || ' berstatus ' || l_status || ' dan tidak dapat diajukan.');
      end if;

      if p_doc_type = 'PR' then
         select count(*) into l_cnt from pur_requisition_line where pr_id = p_doc_id;
         if l_cnt = 0 then
            raise_application_error(-20103, 'PR ' || l_doc_no || ' belum memiliki baris item.');
         end if;
         check_pr_budget(p_doc_id);
      elsif p_doc_type = 'PRJ' then
         select count(*) into l_cnt from prj_wbs where project_id = p_doc_id;
         if l_cnt = 0 then
            raise_application_error(-20104, 'Proyek ' || l_doc_no || ' belum memiliki WBS/budget.');
         end if;
      end if;

      select * into l_type from sys_doc_type where doc_type = p_doc_type;

      if l_type.approver1_role is null then
         set_doc_status(p_doc_type, p_doc_id, 'APPROVED');
      else
         set_doc_status(p_doc_type, p_doc_id, 'SUBMITTED');
         create_step(p_doc_type, p_doc_id, 1, l_type.approver1_role, mbms_sec.app_user);
      end if;
   end submit;

   function can_act_yn (p_approval_id in number) return varchar2 is
      l_appr sys_approval%rowtype;
   begin
      select * into l_appr from sys_approval where approval_id = p_approval_id;
      if l_appr.status <> 'PENDING' then
         return 'N';
      end if;
      if upper(l_appr.requested_by) = upper(mbms_sec.app_user) then
         return 'N';  -- maker-checker
      end if;
      return mbms_sec.has_role_yn(l_appr.approver_role);
   exception
      when no_data_found then return 'N';
   end can_act_yn;

   procedure assert_can_act (p_appr in sys_approval%rowtype) is
   begin
      if p_appr.status <> 'PENDING' then
         raise_application_error(-20105, 'Approval ini sudah diproses (' || p_appr.status || ').');
      end if;
      if upper(p_appr.requested_by) = upper(mbms_sec.app_user) then
         raise_application_error(-20106, 'Segregation of duties: pengaju tidak boleh menyetujui dokumennya sendiri.');
      end if;
      if not mbms_sec.has_role(p_appr.approver_role) then
         raise_application_error(-20107, 'Anda tidak memiliki role ' || p_appr.approver_role || ' untuk approval ini.');
      end if;
   end assert_can_act;

   procedure approve (p_approval_id in number, p_note in varchar2 default null) is
      l_appr sys_approval%rowtype;
      l_type sys_doc_type%rowtype;
   begin
      select * into l_appr from sys_approval where approval_id = p_approval_id for update;
      assert_can_act(l_appr);

      update sys_approval
         set status = 'APPROVED', acted_by = mbms_sec.app_user, acted_on = sysdate, note = p_note
       where approval_id = p_approval_id;

      select * into l_type from sys_doc_type where doc_type = l_appr.doc_type;

      if l_appr.approval_level = 1
         and l_type.approver2_role is not null
         and nvl(l_appr.amount,0) > l_type.level2_limit
      then
         create_step(l_appr.doc_type, l_appr.doc_id, 2, l_type.approver2_role, l_appr.requested_by);
      else
         set_doc_status(l_appr.doc_type, l_appr.doc_id, 'APPROVED');
      end if;
   end approve;

   procedure reject (p_approval_id in number, p_note in varchar2 default null) is
      l_appr sys_approval%rowtype;
   begin
      select * into l_appr from sys_approval where approval_id = p_approval_id for update;
      assert_can_act(l_appr);
      if p_note is null then
         raise_application_error(-20108, 'Alasan penolakan wajib diisi.');
      end if;

      update sys_approval
         set status = 'REJECTED', acted_by = mbms_sec.app_user, acted_on = sysdate, note = p_note
       where approval_id = p_approval_id;

      set_doc_status(l_appr.doc_type, l_appr.doc_id, 'REJECTED');
   end reject;

end mbms_approval;
/

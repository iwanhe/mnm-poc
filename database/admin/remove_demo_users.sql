-- =============================================================================
-- MBMS MVP - Hapus user demo (akun workspace APEX) + role MBMS-nya
-- Kebalikan dari create_demo_users.sql. HANYA untuk sandbox.
-- Akun lain (mis. akun Anda sendiri) dan role-nya tidak disentuh.
-- Jalankan lewat SQL Workshop > SQL Scripts (atau SQLcl), sebagai workspace administrator.
-- =============================================================================
set serveroutput on

declare
   c_workspace constant varchar2(100) := null;  -- isi bila dijalankan di luar SQL Workshop, contoh: 'KCSI'
   l_users     apex_t_varchar2 := apex_t_varchar2(
      'MBMS_ADMIN', 'MBMS_SALES', 'MBMS_PRINT_MGR', 'MBMS_PM', 'MBMS_ENG_MGR',
      'MBMS_DIRECTOR', 'MBMS_PROC', 'MBMS_WH', 'MBMS_FIN', 'MBMS_E2E');
   l_exists    number;
begin
   if c_workspace is not null then
      apex_util.set_workspace(p_workspace => c_workspace);
   end if;

   for i in 1 .. l_users.count loop
      delete from sys_user_role where username = l_users(i);

      select count(*) into l_exists from apex_workspace_apex_users where user_name = l_users(i);
      if l_exists > 0 then
         apex_util.remove_user(p_user_name => l_users(i));
         dbms_output.put_line(rpad(l_users(i), 18) || ' dihapus');
      else
         dbms_output.put_line(rpad(l_users(i), 18) || ' tidak ada');
      end if;
   end loop;

   commit;
end;
/

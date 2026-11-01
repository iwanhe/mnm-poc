-- =============================================================================
-- MBMS MVP - Buat user demo (akun workspace APEX) + daftarkan role MBMS
--
-- Jalankan SETELAH database/mbms_install.sql, login sebagai workspace administrator:
--   SQL Workshop > SQL Scripts > Upload > Run, lalu buka hasil run (View Results)
--   untuk melihat output berisi password. Baris "set serveroutput on" diabaikan di sana.
--   Alternatif: SQLcl (isi c_workspace di bawah).
--   SQL Commands juga bisa: tempel HANYA blok declare ... end; (tanpa baris set dan "/").
--
-- Aman dijalankan ulang:
--   - user yang sudah ada tidak diubah (password tetap)
--   - role yang sudah terdaftar tidak diduplikasi
--
-- Password:
--   - c_password = null  -> password acak per user, DITAMPILKAN SEKALI di output (catat!)
--   - c_password = '...' -> semua user memakai password itu (harus memenuhi password policy workspace)
--
-- HANYA untuk sandbox dengan data dummy. Jangan simpan password di repository.
-- =============================================================================
set serveroutput on

declare
   -- ===== Ubah sesuai kebutuhan ==============================================
   c_password     constant varchar2(100) := null;          -- null = password acak per user
   c_email_domain constant varchar2(100) := 'example.com'; -- email dummy: <username>@<domain>
   c_workspace    constant varchar2(100) := null;          -- isi bila dijalankan di luar SQL Workshop (mis. SQLcl), contoh: 'KCSI'
   c_extra_admin  constant varchar2(255) := null;          -- akun workspace Anda sendiri untuk didaftarkan sebagai ADMIN MBMS, contoh: 'IWAN.HERDIAN'
   -- ==========================================================================

   procedure add_user (p_user in varchar2, p_roles in varchar2, p_first_name in varchar2) is
      l_user   varchar2(255) := upper(p_user);
      l_pwd    varchar2(100);
      l_exists number;
   begin
      select count(*)
        into l_exists
        from apex_workspace_apex_users
       where user_name = l_user;

      if l_exists = 0 then
         -- huruf besar + kecil + angka + tanda baca, untuk memenuhi password policy umum
         l_pwd := coalesce(c_password, 'Mb' || dbms_random.string('x', 8) || '#' || trunc(dbms_random.value(10, 99)));
         apex_util.create_user(
            p_user_name                    => l_user,
            p_first_name                   => p_first_name,
            p_last_name                    => 'MBMS Demo',
            p_email_address                => lower(l_user) || '@' || c_email_domain,
            p_web_password                 => l_pwd,
            p_change_password_on_first_use => 'N');
         dbms_output.put_line(rpad(l_user, 18) || ' dibuat      password: ' || l_pwd);
      else
         dbms_output.put_line(rpad(l_user, 18) || ' sudah ada   (password tidak diubah)');
      end if;

      if p_roles is not null then
         for r in (select trim(column_value) role_code from table(apex_string.split(p_roles, ','))) loop
            merge into sys_user_role t
            using (select l_user username, upper(r.role_code) role_code from dual) s
               on (t.username = s.username and t.role_code = s.role_code)
             when not matched then
                  insert (username, role_code) values (s.username, s.role_code);
            dbms_output.put_line(rpad(' ', 18) || ' role: ' || upper(r.role_code));
         end loop;
      end if;
   end add_user;
begin
   if c_workspace is not null then
      apex_util.set_workspace(p_workspace => c_workspace);
   end if;

   --        username          role MBMS (pisahkan koma)  nama depan
   add_user('MBMS_ADMIN',     'ADMIN',                   'Admin');
   add_user('MBMS_SALES',     'SALES',                   'Sales');
   add_user('MBMS_PRINT_MGR', 'PRINT_MGR',               'Printing Manager');
   add_user('MBMS_PM',        'PROJECT_MGR',             'Project Manager');
   add_user('MBMS_ENG_MGR',   'ENG_MGR',                 'Engineering Manager');
   add_user('MBMS_DIRECTOR',  'DIRECTOR',                'Director');
   add_user('MBMS_PROC',      'PROCUREMENT',             'Procurement');
   add_user('MBMS_WH',        'WAREHOUSE',               'Warehouse');
   add_user('MBMS_FIN',       'FINANCE',                 'Finance');
   add_user('MBMS_E2E',       null,                      'E2E Test');   -- akun test otomatis, tanpa role

   -- Akun workspace yang sudah ada (mis. akun Anda) -> hanya daftarkan role ADMIN, tidak membuat user baru
   if c_extra_admin is not null then
      merge into sys_user_role t
      using (select upper(c_extra_admin) username, 'ADMIN' role_code from dual) s
         on (t.username = s.username and t.role_code = s.role_code)
       when not matched then
            insert (username, role_code) values (s.username, s.role_code);
      dbms_output.put_line(rpad(upper(c_extra_admin), 18) || ' role: ADMIN (akun sudah ada)');
   end if;

   commit;
   dbms_output.put_line('Selesai. Catat password di atas; password acak tidak disimpan di mana pun.');
end;
/

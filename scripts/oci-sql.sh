#!/usr/bin/env bash
# Jalankan perintah SQLcl (dari stdin) ke Autonomous Database di OCI memakai wallet.
# Password tidak pernah dikirim sebagai argumen proses; koneksi dibuat lewat stdin.
#
# Env wajib:
#   SQLCL_BIN      path SQLcl, mis. /opt/sqlcl/bin/sql
#   ADB_WALLET     path wallet zip (Wallet_xxx.zip)
#   DB_USERNAME    schema, mis. XTDCLATRX
#   DB_PASSWORD    password schema
#   DB_TNS_ALIAS   alias di tnsnames.ora wallet, mis. xxx_high
#
# Contoh:
#   scripts/oci-sql.sh <<'SQL'
#   select user from dual;
#   SQL
set -euo pipefail

for v in SQLCL_BIN ADB_WALLET DB_USERNAME DB_PASSWORD DB_TNS_ALIAS; do
  if [[ -z "${!v:-}" ]]; then
    echo "Env $v belum di-set." >&2
    exit 2
  fi
done

if [[ "$DB_PASSWORD" == *'"'* ]]; then
  echo "DB_PASSWORD tidak boleh mengandung tanda kutip ganda (\")." >&2
  exit 2
fi

{
  echo "set cloudconfig $ADB_WALLET"
  echo "whenever sqlerror exit failure"
  echo "whenever oserror exit failure"
  echo "connect $DB_USERNAME/\"$DB_PASSWORD\"@$DB_TNS_ALIAS"
  echo "set serveroutput on size unlimited"
  echo "set feedback on"
  cat
  echo "exit"
} | "$SQLCL_BIN" -S /nolog

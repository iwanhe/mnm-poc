#!/usr/bin/env bash
# Gabungkan database/install/0*.sql menjadi database/mbms_install.sql (untuk SQL Workshop > SQL Scripts)
set -euo pipefail
cd "$(dirname "$0")/../database"
{
  echo "-- MBMS MVP - install gabungan untuk oracleapex.com (SQL Workshop > SQL Scripts)"
  echo "-- File ini digenerate dari database/install/0*.sql oleh scripts/build-install-sql.sh. Jangan diedit langsung."
  for f in install/0*.sql; do echo; echo "-- >>> $f"; cat "$f"; done
} > mbms_install.sql
echo "OK: database/mbms_install.sql"

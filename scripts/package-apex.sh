#!/usr/bin/env bash
# Zip aplikasi APEXlang untuk diupload via App Builder > Import (oracleapex.com).
# Isi zip: application.apx dan folder aplikasi langsung di root zip.
set -euo pipefail
cd "$(dirname "$0")/.."
APP_DIR=apex/mbms
OUT=dist/mbms-apexlang.zip
mkdir -p dist
rm -f "$OUT"
(cd "$APP_DIR" && zip -qr -X "../../$OUT" . -x '*.DS_Store')
echo "OK: $OUT"

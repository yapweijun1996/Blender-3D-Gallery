#!/usr/bin/env bash
set -uo pipefail
export PATH=/home/ai-agent/.local/lib/node22/bin:$PATH
unset BATCH_ASSET_IDS MALL_QA_ASSETS
cd "$(dirname "$0")/repo"
O="$PWD/docs/verification/sgmy-fifty-04/integration";mkdir -p "$O"
fail=0
run(){ name="$1"; shift; echo "START $name $(date -u +%FT%TZ)"; "$@" > "$O/$name.log" 2>&1; rc=$?; printf '%s\t%s\n' "$name" "$rc" | tee -a "$O/status.tsv"; if [ "$rc" != 0 ];then fail=1;tail -65 "$O/$name.log";fi; }
run preservation-start python3 ../verify-imports.py
run unit npm test
run build npm run build
run library env TEST_ARTIFACT_DIR="$O/library" node scripts/test-library-browser.mjs
run lifecycle env TEST_ARTIFACT_DIR="$O/lifecycle" node scripts/test-gallery-loading.mjs
run domestic-browser env MALL_QA_DIR="$O/domestic-browser" node scripts/test-domestic011-browser.mjs
run retail-browser env MALL_QA_DIR="$O/retail-browser" node scripts/test-retail127-browser.mjs
run retail-animation env MALL_QA_DIR="$O/retail-animation" node scripts/test-retail127-animation-browser.mjs
run carehotel-browser env MALL_QA_DIR="$O/carehotel-browser" node scripts/test-carehotel04-browser.mjs
run carehotel-animation env MALL_QA_DIR="$O/carehotel-animation" node scripts/test-carehotel04-animation-browser.mjs
run legacy-preview node scripts/test-preview-config.mjs dist "$O/legacy-preview"
run preservation-end python3 ../verify-imports.py
exit "$fail"

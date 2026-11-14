#!/usr/bin/env bash
set -uo pipefail
export PATH=/home/ai-agent/.local/lib/node22/bin:$PATH
unset BATCH_ASSET_IDS MALL_QA_ASSETS
cd "$(dirname "$0")/repo"
O="$PWD/docs/verification/sgmy-fifty-05/integration";mkdir -p "$O"
fail=0
run(){ name="$1"; shift; echo "START $name $(date -u +%FT%TZ)"; "$@" > "$O/$name.log" 2>&1; rc=$?; printf '%s\t%s\n' "$name" "$rc" | tee -a "$O/status.tsv"; if [ "$rc" != 0 ];then fail=1;tail -65 "$O/$name.log";fi; }
run preservation-start python3 ../verify-imports.py
run unit npm test
run build npm run build
run library env TEST_ARTIFACT_DIR="$O/library" node scripts/test-library-browser.mjs
run lifecycle env TEST_ARTIFACT_DIR="$O/lifecycle" node scripts/test-gallery-loading.mjs
run workplace-browser env MALL_QA_DIR="$O/workplace-browser" node scripts/test-workplace029-browser.mjs
run transport-browser env MALL_QA_DIR="$O/transport-browser" node scripts/test-transport039-browser.mjs
run transport-animation env MALL_QA_DIR="$O/transport-animation" node scripts/test-transport039-animation-browser.mjs
run cityshells-browser env MALL_QA_DIR="$O/cityshells-browser" node scripts/test-cityshells05-browser.mjs
run cityshells-animation env MALL_QA_DIR="$O/cityshells-animation" node scripts/test-cityshells05-animation-browser.mjs
run legacy-preview node scripts/test-preview-config.mjs dist "$O/legacy-preview"
run preservation-end python3 ../verify-imports.py
exit "$fail"

#!/bin/bash
set -uo pipefail
export PATH=/home/ai-agent/.local/lib/node22/bin:$PATH
unset BATCH_ASSET_IDS MALL_QA_ASSETS
cd "$(dirname "$0")/repo"
O="$PWD/docs/verification/sgmy-fifty-06/latest-main";mkdir -p "$O"
fail=0
run(){ name="$1";shift;echo "START $name $(date -u +%FT%TZ)";"$@" > "$O/$name.log" 2>&1;rc=$?;printf '%s\t%s\n' "$name" "$rc"|tee -a "$O/status.tsv";if [ "$rc" != 0 ];then fail=1;tail -65 "$O/$name.log";fi;}
run preservation-start python3 ../verify-imports.py
run unit bash ../run-unit-fixture.sh
run build npm run build
run library env TEST_ARTIFACT_DIR="$O/library" node scripts/test-library-browser.mjs
run lifecycle env TEST_ARTIFACT_DIR="$O/lifecycle" node scripts/test-gallery-loading.mjs
run preservation-end python3 ../verify-imports.py
exit "$fail"

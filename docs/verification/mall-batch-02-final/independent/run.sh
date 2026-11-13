#!/bin/bash
set +e
export PATH=/home/ai-agent/.local/lib/node22/bin:$PATH
for id in escalator-handrail lift-call-panel lift-floor-indicator emergency-exit-door fire-hose-reel-cabinet sprinkler-head cctv-camera digital-advertising-screen wayfinding-ceiling-sign food-court-tray-station; do
 p=review-fixtures/models/mall-$id
 /srv/agent-workstation/workspaces/blender-mall-four-20261112/blender-local.sh --threads 2 --python-exit-code 1 --python "$p/inspect_sources.py" >review-results/$id-source.log 2>&1
 echo "$id source $?" >>review-results/exitcodes.txt
 node "$p/validate.mjs" >review-results/$id-geometry.log 2>&1
 echo "$id geometry $?" >>review-results/exitcodes.txt
 node "$p/verify_source_edit.mjs" >review-results/$id-edit.log 2>&1
 echo "$id edit $?" >>review-results/exitcodes.txt
done
cat review-results/exitcodes.txt

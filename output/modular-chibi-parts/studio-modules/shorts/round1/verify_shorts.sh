#!/bin/sh
set -eu
cd "$(dirname "$0")"
node validate_shorts.cjs
sh run_blender.sh inspect_export.py
sh check_all.sh
node summarize_checks.cjs
sh run_blender.sh render_shorts.py
sh run_blender.sh audit_render_details.py

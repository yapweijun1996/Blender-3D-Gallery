#!/bin/sh
set -eu
cd "$(dirname "$0")"
for bank in shared sit carry; do
    sh run_blender.sh check_shorts.py -- "$bank"
    sh run_blender.sh check_shorts.py -- "$bank" --triangles
done

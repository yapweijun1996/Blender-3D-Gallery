#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
: "${BLENDER_BIN:?Set BLENDER_BIN to the Blender 5.1.2 executable}"
mkdir -p .qa contact-sheets
swiftc -module-cache-path .qa/swift-cache source/graphics.swift -o .qa/graphics
for asset in concourse circle downtown entrance; do
    .qa/graphics atlas ".qa/atlas_${asset}.jpg" "$asset"
done
if [ -n "${BLENDER_GUARD_DYLIB:-}" ]; then
    export DYLD_INSERT_LIBRARIES="$BLENDER_GUARD_DYLIB"
fi
export TMPDIR="$PWD/.qa"
"$BLENDER_BIN" -b -noaudio -t 2 --factory-startup --python-exit-code 1 --python source/build.py -- "$@"
if [ "${1:-}" = "--export-only" ]; then
    exit
fi
for platform in circle downtown; do
    model="bayfront_platform_${platform}"
    .qa/graphics sheet "contact-sheets/$model.jpg" "$model" 'Front / roof removed' 'Rear / roof removed' 'Plan / roof removed' 'Platform approach' 'Screen doors and boarding marks' 'Seating and route maps'
done
.qa/graphics sheet contact-sheets/bayfront_concourse.jpg bayfront_concourse 'Front / ceiling removed' 'Rear / ceiling removed' 'Plan / ceiling removed' 'Faregates and service centre' 'Concourse escalator well' 'Passenger eye level'
.qa/graphics sheet contact-sheets/bayfront_entrance.jpg bayfront_entrance 'Entrance three-quarter' 'Exit B elevation' 'Rear glazing' 'Plan / roof removed' 'Descending escalators' 'Street approach'

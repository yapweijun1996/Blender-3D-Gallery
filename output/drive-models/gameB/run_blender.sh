#!/bin/sh
set -eu
cd "$(dirname "$0")"
: "${VEHICLE_BLENDER_DIR:=/private/tmp/claude-501/-Users-yapweijun--claude-spares-spare-Iu3lC0/26a84d71-25c7-41e6-b903-49317aeebb05/scratchpad/modular}"
export DYLD_INSERT_LIBRARIES="$VEHICLE_BLENDER_DIR/guard.dylib"
script=$1
shift
exec "$VEHICLE_BLENDER_DIR/B/Blender.app/Contents/MacOS/Blender" -b -noaudio -t 2 --python-exit-code 1 --python "$script" -- "$@"

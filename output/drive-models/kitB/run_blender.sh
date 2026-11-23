#!/bin/sh
# Set KIT_BLENDER_DIR to the directory containing the guarded Blender bundle.
set -eu
cd "$(dirname "$0")"
: "${KIT_BLENDER_DIR:=/private/tmp/claude-501/-Users-yapweijun--claude-spares-spare-Iu3lC0/26a84d71-25c7-41e6-b903-49317aeebb05/scratchpad/modular}"
export DYLD_INSERT_LIBRARIES="$KIT_BLENDER_DIR/guard.dylib"
script=$1
shift
exec "$KIT_BLENDER_DIR/B/Blender.app/Contents/MacOS/Blender" -b -noaudio -t 2 --python-exit-code 1 --python "$script" -- "$@"

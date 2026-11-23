#!/bin/sh
set -eu
root=$(cd "$(dirname "$0")" && pwd)
base=/private/tmp/claude-501/-Users-yapweijun--claude-spares-spare-Iu3lC0/26a84d71-25c7-41e6-b903-49317aeebb05/scratchpad/modular
mkdir -p "$root/.runtime"
export TMPDIR="$root/.runtime" BLENDER_USER_RESOURCES="$root/.runtime/blender" PYTHONDONTWRITEBYTECODE=1
export DYLD_INSERT_LIBRARIES="$base/guard.dylib"
exec "$base/B/Blender.app/Contents/MacOS/Blender" -b -noaudio --factory-startup --python-exit-code 1 --python "$@"

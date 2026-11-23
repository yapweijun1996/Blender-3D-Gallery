#!/bin/sh
set -eu
cd "$(dirname "$0")"
run_dir=$(pwd)
blender_bundle=/private/tmp/claude-501/-Users-yapweijun--claude-spares-spare-Iu3lC0/26a84d71-25c7-41e6-b903-49317aeebb05/scratchpad/modular
mkdir -p "$run_dir/.runtime"
export TMPDIR="$run_dir/.runtime/"
export BLENDER_USER_RESOURCES="$run_dir/.runtime/blender"
export XDG_CACHE_HOME="$run_dir/.runtime/cache"
export PYTHONDONTWRITEBYTECODE=1
export DYLD_INSERT_LIBRARIES="$blender_bundle/guard.dylib"
exec "$blender_bundle/B/Blender.app/Contents/MacOS/Blender" -b -t 6 -noaudio --factory-startup --disable-autoexec --python-exit-code 1 --python "$@"

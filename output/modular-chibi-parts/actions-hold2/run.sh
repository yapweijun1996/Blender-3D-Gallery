#!/bin/sh
set -eu
cd "$(dirname "$0")"
run_dir=$(pwd)
bundle=/private/tmp/claude-501/-Users-yapweijun--claude-spares-spare-Iu3lC0/26a84d71-25c7-41e6-b903-49317aeebb05/scratchpad/modular
mkdir -p .runtime checks props renders
export TMPDIR="$run_dir/.runtime/" BLENDER_USER_RESOURCES="$run_dir/.runtime/blender" XDG_CACHE_HOME="$run_dir/.runtime/cache" PYTHONDONTWRITEBYTECODE=1
export DYLD_INSERT_LIBRARIES="$bundle/guard.dylib"
exec "$bundle/B/Blender.app/Contents/MacOS/Blender" -b -t 5 -noaudio --factory-startup --disable-autoexec --python-exit-code 1 --python "$@"

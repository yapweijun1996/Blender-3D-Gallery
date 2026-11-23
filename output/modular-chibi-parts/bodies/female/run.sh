#!/bin/sh
set -eu
cd "$(dirname "$0")"
runtime="$(pwd)/.runtime"
mkdir -p "$runtime"
export TMPDIR="$runtime/" BLENDER_USER_RESOURCES="$runtime/blender" XDG_CACHE_HOME="$runtime/cache" PYTHONDONTWRITEBYTECODE=1
bundle=/private/tmp/claude-501/-Users-yapweijun--claude-spares-spare-Iu3lC0/26a84d71-25c7-41e6-b903-49317aeebb05/scratchpad/modular
export DYLD_INSERT_LIBRARIES="$bundle/guard.dylib"
threads="${FEMALE_BLENDER_THREADS:-4}"
exec "$bundle/B/Blender.app/Contents/MacOS/Blender" -b -t "$threads" -noaudio --factory-startup --disable-autoexec --python-exit-code 1 --python "$@"

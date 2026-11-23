#!/bin/sh
set -eu
cd "$(dirname "$0")"
scratch=/private/tmp/claude-501/-Users-yapweijun--claude-spares-spare-Iu3lC0/26a84d71-25c7-41e6-b903-49317aeebb05/scratchpad/modular
export TMPDIR="$PWD/" BLENDER_USER_RESOURCES="$PWD/.blender" PYTHONDONTWRITEBYTECODE=1
export DYLD_INSERT_LIBRARIES="$scratch/guard.dylib"
exec "$scratch/B/Blender.app/Contents/MacOS/Blender" -b -t "${PANTS_THREADS:-6}" -noaudio --factory-startup --disable-autoexec --python-exit-code 1 --python "$@"

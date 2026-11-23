#!/bin/sh
set -eu
dir=$(cd "$(dirname "$0")/.." && pwd)
runtime=/private/tmp/claude-501/-Users-yapweijun--claude-spares-spare-Iu3lC0/26a84d71-25c7-41e6-b903-49317aeebb05/scratchpad/modular
mkdir -p "$dir/work/temp"
export TMPDIR="$dir/work/temp" PYTHONDONTWRITEBYTECODE=1 BLENDER_USER_RESOURCES="$dir/work/temp/blender"
export DYLD_INSERT_LIBRARIES="$runtime/guard.dylib"
exec "$runtime/B/Blender.app/Contents/MacOS/Blender" -b -noaudio -t 5 --python-exit-code 1 "$@"

#!/bin/sh
set -eu
root=$(cd "$(dirname "$0")/.." && pwd)
cd "$root"
runtime="$root/.work"
mkdir -p "$runtime"/tmp "$runtime"/cache "$runtime"/config
export TMPDIR="$runtime/tmp/" XDG_CACHE_HOME="$runtime/cache" BLENDER_USER_RESOURCES="$runtime/config" PYTHONDONTWRITEBYTECODE=1
installation=/private/tmp/claude-501/-Users-yapweijun--claude-spares-spare-Iu3lC0/26a84d71-25c7-41e6-b903-49317aeebb05/scratchpad/modular
binary="$installation/B/Blender.app/Contents/MacOS/Blender"
exec env DYLD_INSERT_LIBRARIES="$installation/guard.dylib" "$binary" -b -noaudio -t 4 --python-exit-code 1 --python "$@"

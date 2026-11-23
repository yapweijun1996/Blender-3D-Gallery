#!/bin/sh
set -eu
cd "$(dirname "$0")"
root=$(pwd)
runtime=$(mktemp -d "$root/.blender-run.XXXXXXXX")
trap 'rm -rf "$runtime"' EXIT
mkdir -p "$runtime/tmp" "$runtime/cache" "$runtime/config"
export TMPDIR="$runtime/tmp/"
export BLENDER_USER_RESOURCES="$runtime/config" XDG_CACHE_HOME="$runtime/cache" PYTHONDONTWRITEBYTECODE=1
script=$1
shift
DYLD_INSERT_LIBRARIES=/private/tmp/claude-501/-Users-yapweijun--claude-spares-spare-Iu3lC0/26a84d71-25c7-41e6-b903-49317aeebb05/scratchpad/modular/guard.dylib /private/tmp/claude-501/-Users-yapweijun--claude-spares-spare-Iu3lC0/26a84d71-25c7-41e6-b903-49317aeebb05/scratchpad/modular/B/Blender.app/Contents/MacOS/Blender -b -noaudio --python-exit-code 1 --python "$script" -- "$@"

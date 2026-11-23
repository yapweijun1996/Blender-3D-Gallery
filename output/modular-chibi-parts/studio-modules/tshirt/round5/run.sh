#!/bin/sh
set -eu
cd "$(dirname "$0")"
base=/private/tmp/claude-501/-Users-yapweijun--claude-spares-spare-Iu3lC0/26a84d71-25c7-41e6-b903-49317aeebb05/scratchpad/modular
mkdir -p .runtime/tmp .runtime/cache .runtime/config
export TMPDIR="$PWD/.runtime/tmp" XDG_CACHE_HOME="$PWD/.runtime/cache" BLENDER_USER_CONFIG="$PWD/.runtime/config"
export PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 OMP_NUM_THREADS=2
export DYLD_INSERT_LIBRARIES="$base/guard.dylib"
exec "$base/B/Blender.app/Contents/MacOS/Blender" -b -noaudio --disable-autoexec --python-exit-code 1 --python "$@"

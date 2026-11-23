#!/bin/sh
set -eu
cd "$(dirname "$0")"
scratch=/private/tmp/claude-501/-Users-yapweijun--claude-spares-spare-Iu3lC0/26a84d71-25c7-41e6-b903-49317aeebb05/scratchpad/modular
mkdir -p .work
export TMPDIR="$PWD/.work/"
export DYLD_INSERT_LIBRARIES="$scratch/guard.dylib"
export PYTHONDONTWRITEBYTECODE=1
export VECLIB_MAXIMUM_THREADS=1
exec "$scratch/B/Blender.app/Contents/MacOS/Blender" -b -noaudio -t 5 --factory-startup --disable-autoexec --python-exit-code 1 --python fit_dress_r5.py -- "$@"

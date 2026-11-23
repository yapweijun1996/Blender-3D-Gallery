#!/bin/sh
set -eu
mod=/private/tmp/claude-501/-Users-yapweijun--claude-spares-spare-Iu3lC0/26a84d71-25c7-41e6-b903-49317aeebb05/scratchpad/modular
export TMPDIR="$PWD"
export DYLD_INSERT_LIBRARIES="$mod/guard.dylib"
export PYTHONDONTWRITEBYTECODE=1
exec "$mod/B/Blender.app/Contents/MacOS/Blender" -b -noaudio -t 2 --disable-autoexec --python-exit-code 1 "$@"

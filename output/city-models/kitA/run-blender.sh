#!/bin/zsh
set -eu
kit=${0:A:h}
bundle=/private/tmp/claude-501/-Users-yapweijun--claude-spares-spare-Iu3lC0/26a84d71-25c7-41e6-b903-49317aeebb05/scratchpad/modular
export DYLD_INSERT_LIBRARIES="$bundle/guard.dylib"
export TMPDIR="$kit/.work"
cd "$kit"
mkdir -p .work
exec "$bundle/B/Blender.app/Contents/MacOS/Blender" -b -noaudio -t 2 --disable-autoexec --python-exit-code 1 --python "$1" -- "${@:2}"

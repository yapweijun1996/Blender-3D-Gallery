#!/bin/zsh
set -eu
cd "${0:A:h}"
runtime=${STREETKIT_BLENDER_ROOT:-/private/tmp/claude-501/-Users-yapweijun--claude-spares-spare-Iu3lC0/26a84d71-25c7-41e6-b903-49317aeebb05/scratchpad/modular}
DYLD_INSERT_LIBRARIES="$runtime/guard.dylib" "$runtime/B/Blender.app/Contents/MacOS/Blender" -b -noaudio -t 2 --python-exit-code 1 --python build.py -- "$@"

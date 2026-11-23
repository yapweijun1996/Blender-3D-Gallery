#!/bin/zsh
base=/private/tmp/claude-501/-Users-yapweijun--claude-spares-spare-Iu3lC0/26a84d71-25c7-41e6-b903-49317aeebb05/scratchpad/modular
exec env DYLD_INSERT_LIBRARIES="$base/guard.dylib" "$base/B/Blender.app/Contents/MacOS/Blender" -b -noaudio --python-exit-code 2 "$@"

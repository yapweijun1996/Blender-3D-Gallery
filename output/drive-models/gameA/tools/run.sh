#!/bin/sh
# Run from any directory with this checkout's guarded Blender installation.
set -eu
cd "$(dirname "$0")/.."
guard_dir=${GAMEA_BLENDER_DIR:-'/private/tmp/claude-501/-Users-yapweijun--claude-spares-spare-Iu3lC0/26a84d71-25c7-41e6-b903-49317aeebb05/scratchpad/modular'}
mkdir -p .work/blender-user
export TMPDIR="$PWD/.work"
export BLENDER_USER_RESOURCES="$PWD/.work/blender-user"
script=$1
shift
exec env DYLD_INSERT_LIBRARIES="$guard_dir/guard.dylib" "$guard_dir/B/Blender.app/Contents/MacOS/Blender" -b -noaudio -t 2 --python-exit-code 1 --python "$script" -- "$@"

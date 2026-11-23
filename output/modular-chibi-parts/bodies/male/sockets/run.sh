#!/bin/sh
set -eu
cd "$(dirname "$0")"
run_dir=$(pwd)
case ${SOCKET_THREADS:-2} in
    1|2) ;;
    *) echo "SOCKET_THREADS must be 1 or 2" >&2; exit 2 ;;
esac
blender_bundle=/private/tmp/claude-501/-Users-yapweijun--claude-spares-spare-Iu3lC0/26a84d71-25c7-41e6-b903-49317aeebb05/scratchpad/modular
mkdir -p "$run_dir/.runtime"
export TMPDIR="$run_dir/.runtime/" BLENDER_USER_RESOURCES="$run_dir/.runtime/blender" XDG_CACHE_HOME="$run_dir/.runtime/cache"
export PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1
export DYLD_INSERT_LIBRARIES="$blender_bundle/guard.dylib"
exec "$blender_bundle/B/Blender.app/Contents/MacOS/Blender" -b -noaudio -t "${SOCKET_THREADS:-2}" --factory-startup --disable-autoexec --python-exit-code 1 --python-expr 'import os,sys; sys.path.insert(0,os.getcwd()); sys.dont_write_bytecode=True' --python "$@"

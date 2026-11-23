#!/bin/sh
set -eu
cd "$(dirname "$0")"
item=$1
round=$2
name="$item-r$round"
node repair_tangents.mjs "$name.glb"
node validate.mjs "$name.glb" "qa/$name.validator.json"
./run.sh gate_module.py -- "$name.glb" "$item" "qa/$name.gate.json" >"qa/$name.gate.log" 2>&1

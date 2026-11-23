#!/bin/sh
set -eu
cd "$(dirname "$0")"
if [ "$#" -eq 0 ]; then
    set -- top-hoodie top-jacket bottom-shorts bottom-skirt shoes-boots
fi
for item do
    if [ ! -f "qa/$item.result.json" ]; then
        for round in 1 2 3; do
            name="$item-r$round"
            if [ ! -f "qa/$name.gate.json" ]; then
                ./run.sh build_wardrobe.py -- "$item" "$round" > "qa/$name.log" 2>&1
            fi
            if python3 results.py "$item" "$round"; then
                break
            else
                status=$?
                if [ "$status" -ne 2 ]; then
                    exit "$status"
                fi
            fi
        done
    fi
    if [ ! -f "renders/$item/manifest.json" ]; then
        selected=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["file"])' "qa/$item.result.json")
        ./run.sh render_item.py -- "$selected" "$item" > "qa/$item.render.log" 2>&1
        python3 results.py notes
    fi
done

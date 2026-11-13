# Wooden Pallet (backlog 142)

Original independent metre-scale Blender Python asset. Blender +Z up/-Y front; GLB +Y up/+Z front. Editable mesh/material components and meaningful demonstration clips where present. No third-party assets or textures.

Local gate PASS; release NEEDS REVIEW. 4440 triangles, 215384 GLB bytes, 26 mesh primitives, 0 clips. Budgets are fixed in backlog.json. Source and exported file hashes: reports/sources.json and reports/assets.json.

## Reproduce
Run from repository root with Blender 4.0.2 and installed project dependencies:
- blender --background --threads 2 --python-exit-code 1 --python models/wooden-pallet/generate.py
- node models/wooden-pallet/validate.mjs
- blender --background --threads 2 --python-exit-code 1 --python models/wooden-pallet/inspect_sources.py
- node models/wooden-pallet/verify_source_edit.mjs
- npm test && npm run build
- MALL_QA_DIR=/tmp/office023-browser node scripts/test-office023-browser.mjs
Optional MALL_QA_ASSETS=wooden-pallet restricts the same three complete browser cases to this asset; full default is 16 assets/48 cases.

Four final studio angles and browser screenshots were actually inspected. Movable assets additionally have inspected frame30 preview (laptop closed, others opened/raised). Source proof reopens the original, changes actual mesh vertices and material roughness, saves/reopens the edited copy, exports without regeneration and checks canonical source is unchanged. Raw clip endpoints and midpoint travel/clearance/restoration are tested.

Desktop Chromium viewport emulation is not real Android/iOS or WebKit verification. Gallery animation playback UI is not implemented. Props are illustrative, not functioning equipment, certified furniture, medical, lifting or fire-safety products. See LICENSE.md. No deployment.

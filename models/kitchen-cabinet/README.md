# Kitchen Cabinet (backlog 053)

Independent original Blender Python asset, with editable mesh/material parts. Metres; Blender +Z up/-Y front, GLB +Y up/+Z front.

Local PASS; release NEEDS REVIEW. 1348 triangles, 77172 GLB bytes, 11 mesh primitives and 2 clips. Fixed upfront budget in backlog.json, final hashes in reports/assets.json and reports/sources.json.

## Reproduce from repository root
- blender --background --threads 2 --python-exit-code 1 --python models/kitchen-cabinet/generate.py
- node models/kitchen-cabinet/validate.mjs
- blender --background --threads 2 --python-exit-code 1 --python models/kitchen-cabinet/inspect_sources.py
- node models/kitchen-cabinet/verify_source_edit.mjs
- npm test && npm run build
- MALL_QA_DIR=/tmp/domestic011-browser node scripts/test-domestic011-browser.mjs

The default browser run covers all 16 assets at three viewports. Optional MALL_QA_ASSETS=kitchen-cabinet selects this asset's same complete 3-case protocol. Every browser output honors MALL_QA_DIR.

Source QA opens the canonical .blend, edits actual mesh vertices and material roughness, saves/reopens a copy, exports without regenerating and verifies canonical SHA-256 unchanged. Four final studio angles and final GLB browser views actually inspected. Animated assets additionally have inspected frame30 previews with raw endpoints, intended midpoint motion, opening/clearance and LoopOnce restoration tests. Static assets have no invented clips.

Physical Android/iOS and WebKit NOT TESTED. Gallery animation playback UI not implemented. Illustrative props, not functioning cooking, refrigeration, dispensing, payment, electrical or plumbing equipment and not engineering/accessibility/safety certification. No external assets or brands. Rights: LICENSE.md. No deployment.

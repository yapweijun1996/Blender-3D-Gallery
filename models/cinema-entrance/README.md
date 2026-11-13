# Cinema Entrance

Original V1 ID 017. Local **PASS**, release **NEEDS REVIEW** pending real Android/iOS and WebKit. No deployment.

## Distinct scope
Cinema admission portal with recessed queue/entrance, acoustic-wall fins and editable neutral ticket/display frames; no film posters/brands.

Blender +Z up/-Y front; GLB +Y up/+Z front; metre units. Components/materials remain editable. Original illustrative proportions, not a surveyed building, landmark, engineering/fire/accessibility certification or functioning payment/security/medical/vehicle system. No brands or external textures/models. See LICENSE.md for rights.

## Artifacts and evidence
- `generate.py`; `sources/cinema-entrance.blend`; `exports/optimized.glb`.
- Four final inspected studio views in `previews/` (PNG and catalog WebP). Animated types additionally have inspected `open.png`.
- 4256 triangles, 229736 GLB bytes, 38 primitives. Fixed pre-generation budget in `backlog.json`.
- `reports/assets.json`: Khronos, exact metric structure, named geometry and animation gates. N/A: static independently editable model.
- `reports/sources.json` and `reports/source-edit/`: independent mesh/material edits saved, reopened and exported without rebuilding; original hash unchanged.
- Browser final evidence mapping: `docs/verification/mall038/browser-final-results.json`; actual final source/export hashes in `asset-results.json`.

## Reproduce
`node models/cinema-entrance/validate.mjs`

`blender --background --threads 2 --python-exit-code 1 --python models/cinema-entrance/inspect_sources.py`

`node models/cinema-entrance/verify_source_edit.mjs`

Global gate: `npm test && npm run build`, then `MALL_QA_DIR=/your/evidence node scripts/test-mall038-browser.mjs`. Browser output paths all honor MALL_QA_DIR. No generic gallery clip playback UI or driving control is claimed. Vehicle wheel clips show a half-turn and return, not full-spin odometry.

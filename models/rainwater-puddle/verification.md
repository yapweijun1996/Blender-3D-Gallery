# Rainwater Puddle verification
2026-11-13; backlog 478. Local **PASS**; release/mobile **NEEDS REVIEW**.

## Verified evidence
- Independent editable Blender4.0.2 source sources/rainwater-puddle.blend, metre units, Blender+Z up/-Y front -> glTF+Y up/+Z front; ground-plane centre datum.
- inspect_source.py reopens source, changes named component +0.2m and material roughness, saves/reopens edited .blend and exports WITHOUT generator regeneration. Original source hash unchanged. See reports/source.json, source-edit.blend, source-edit.glb, source-edit-proof.json and verify_source_edit logs.
- Export 42876 bytes,940 triangles; fixed budgets 180000 bytes/3500 triangles. Khronos zero errors/warnings, finite geometry and semantic component assertions PASS. reports/assets.json.
- Final GLB SHA256: 7abf8a322b3f3d7b1ec01721d7656e2566ac0b9f71283ef193e33f18f44bff41.
- Actual exported GLB hero/front/rear/side preview pixels inspected; all3 current browser initial viewport screenshots inspected. Recognizable simplified geometry, no remaining blocking visible defect identified. Low-poly botanical forms are stylized, not species-identification references; some fine Cycles grain/grazing silhouettes remain.
- Chromium desktop WebGL at1440/768/390: exact GLB bytes/hash, render, orbit/zoom/reset/reopen and canvas-close cleanup PASS. reports/browser-initial/results.json. Responsive viewport tests do not establish real-device compatibility.
- Unit316/316 and build PASS: docs/verification/fifty03-nature/unit-final.log and build-final.log. Existing bundle chunk-size warning retained.
- Physical Android/iOS, Safari/WebKit, thermal/performance testing and combined latest-main integration NOT TESTED here. No deployment or remote action.
## Interaction
Static asset. Independently editable components/materials; no fake interaction or simulation.
## Provenance and limitations
Original geometry/materials; no external model, image, font or brand. Owner-project reuse authorized; public redistribution terms unspecified. No official engineering, scientific or safety claims. Puddle is a shallow static opaque reflective mesh, not fluid simulation; plants do not simulate growth/wind.
## Reproduce from repo root
Set BLENDER to installed Blender wrapper. Browser checks require npm run build.
```sh
"$BLENDER" -b -t 2 --python models/rainwater-puddle/generate.py
node models/rainwater-puddle/validate.mjs
"$BLENDER" -b -t 2 --python models/rainwater-puddle/inspect_source.py
node models/rainwater-puddle/verify_source_edit.mjs
"$BLENDER" -b -t 2 --python models/rainwater-puddle/render_views.py
MALL_QA_DIR=/tmp/fresh-rainwater-puddle-qa node scripts/test-rainwater-puddle.mjs
```
To export a manually edited canonical source without generation, pass --export-source to generate.py. Initial failure logs and changed asset snapshots are retained under docs/verification/fifty03-nature; see corrections.md. Historical binaries are not cataloged as extra assets.

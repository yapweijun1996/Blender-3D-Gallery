# Malaysia House Boundary Wall verification
Date: 2026-11-13. Backlog 324.

## Result
Local asset gate: **PASS**. Release/mobile compatibility: **NEEDS REVIEW**.
No deployment, merge or remote publication performed.

- Original source reopened in Blender 4.0.2; metre units, finite transforms, independent objects and materials checked.
- Source-edit experiment saved a separate edited .blend and GLB; named component moved 0.2 m and exported bounds verified. Original source unchanged. See reports/source.json, source-edit-proof.json, source-edit.blend and source-edit.glb.
- Khronos validation: zero errors and warnings. Bytes, triangle budget, scale, origin and semantic geometry checked by validate.mjs. See reports/assets.json.
- Current GLB SHA-256: 82334407296121bef0e9b4bdf6b7a2357430c2480924a0af52fceaf78688481a; 100896 bytes, 1836 triangles.
- Rendered actual exported GLB hero/front/rear/side views inspected. Recognizable modular proportions and material separation; no blocking geometry defects identified. Front studio previews retain dark backdrop bands; small ground noise and thin-profile silhouette views are presentation limitations, not missing geometry.
- Chromium WebGL at 1440, 768 and 390 px: exact model request/hash, load, orbit, zoom, reset and reopen checks PASS. See reports/browser-final/results.json and screenshots. All three initial viewport screenshots visually inspected.
- Physical Android and iOS hardware, Safari/WebKit, thermal/performance budgets and final combined assembly regression: NOT TESTED here. Responsive Chromium is not evidence of mobile-device certification.
- Unit suite 235/235 and production build PASS in docs/verification/batch09-five/unit-animation-final.log and build-animation-final.log. Legacy application lifecycle tests were not run in this producer workspace.

## Interaction
Static architectural module. Independent editable meshes/materials; no artificial runtime animation.

## Preserved failures and corrections
Initial porch GLB exceeded its unchanged 512000-byte budget; tiny tile bevels were removed while preserving all 88 tiles. Initial wall/roof coplanar overlaps corrected, geometry assertions added. Gate's first animation exported a frame-one time offset; keyframes changed to frames 0/30/60 with unchanged two-second assertions. Initial assets and failed logs remain in docs/verification/batch09-five/initial-assets, gate-before-animation and gate-animation-offset-initial. Do not treat those historical binaries as release assets.

## Reproduction
Run Blender generate.py, then node validate.mjs. Run Blender inspect_source.py and node verify_source_edit.mjs. Run Blender render_views.py and inspect actual images. Run npm test and npm run build; run node scripts/test-malaysia-house-boundary-wall.mjs according to script environment settings.

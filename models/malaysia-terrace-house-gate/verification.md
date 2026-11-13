# Malaysia Terrace House Gate verification
Date: 2026-11-13. Backlog 321.

## Result
Local asset gate: **PASS**. Release/mobile compatibility: **NEEDS REVIEW**.
No deployment, merge or remote publication performed.

- Original source reopened in Blender 4.0.2; metre units, finite transforms, independent objects and materials checked.
- Source-edit experiment saved a separate edited .blend and GLB; named component moved 0.2 m and exported bounds verified. Original source unchanged. See reports/source.json, source-edit-proof.json, source-edit.blend and source-edit.glb.
- Khronos validation: zero errors and warnings. Bytes, triangle budget, scale, origin and semantic geometry checked by validate.mjs. See reports/assets.json.
- Current GLB SHA-256: e5a910036937a3e0a69a0809ed70d9096e4f87bd5ca80865238eaf036603e903; 287260 bytes, 5288 triangles.
- Rendered actual exported GLB hero/front/rear/side views inspected. Recognizable modular proportions and material separation; no blocking geometry defects identified. Front studio previews retain dark backdrop bands; small ground noise and thin-profile silhouette views are presentation limitations, not missing geometry.
- Chromium WebGL at 1440, 768 and 390 px: exact model request/hash, load, orbit, zoom, reset and reopen checks PASS. See reports/browser-animation-final/results.json and screenshots. All three initial viewport screenshots visually inspected.
- Physical Android and iOS hardware, Safari/WebKit, thermal/performance budgets and final combined assembly regression: NOT TESTED here. Responsive Chromium is not evidence of mobile-device certification.
- Unit suite 235/235 and production build PASS in docs/verification/batch09-five/unit-animation-final.log and build-animation-final.log. Legacy application lifecycle tests were not run in this producer workspace.

## Interaction
Two synchronized two-second GLB clips Gate_Left_Open_Close and Gate_Right_Open_Close: closed at 0s, 65-degree open at 1s, closed at 2s. Three.js AnimationMixer verified in Node and real Chromium WebGL; fixed hinges and restored pose checked. Play both clips together. No Gallery playback UI, physics or collision controller.

## Preserved failures and corrections
Initial porch GLB exceeded its unchanged 512000-byte budget; tiny tile bevels were removed while preserving all 88 tiles. Initial wall/roof coplanar overlaps corrected, geometry assertions added. Gate's first animation exported a frame-one time offset; keyframes changed to frames 0/30/60 with unchanged two-second assertions. Initial assets and failed logs remain in docs/verification/batch09-five/initial-assets, gate-before-animation and gate-animation-offset-initial. Do not treat those historical binaries as release assets.

## Reproduction
Run Blender generate.py, then node validate.mjs. Run Blender inspect_source.py and node verify_source_edit.mjs. Run Blender render_views.py and inspect actual images. Run npm test and npm run build; run node scripts/test-malaysia-terrace-house-gate.mjs according to script environment settings.

Animation evidence: reports/animation-proof.json and reports/animation-browser/results.json; browser closed/open/reclosed screenshots inspected. Run node models/malaysia-terrace-house-gate/verify_animation.mjs and scripts/test-terrace-gate-animation.mjs.

# Straits Shophouse Door verification
Date: 2026-11-13. Backlog 401.
Local asset gate **PASS**; release/mobile status **NEEDS REVIEW**. No deployment or remote submission.

## Delivered evidence
- Source sources/straits-shophouse-door.blend reopened with Blender4.0.2, metre units, independent mesh data and finite geometry checked.
- Source-copy component edit +0.2m and material roughness change saved, reopened from edited .blend, exported WITHOUT generator regeneration. Original source SHA unchanged. reports/source.json, source-edit.blend, source-edit.glb and source-edit-proof.json; inspect_source and verify_source_edit logs record material assertion.
- GLB 151464 bytes / 2632 triangles within fixed 500000-byte / 11000-triangle budgets. Khronos zero errors/warnings. SHA256 9aaa22ab3102d1af0c4a643e70190df847d49ecc9aac512d19d67688b4936a8c. reports/assets.json.
- Actual exported GLB studio hero/front/rear/side pixels inspected; all three current Chromium initial viewport screenshots inspected. Recognizable simplified geometry and material separation. Fine Cycles grain, grazing-angle thin silhouettes and stylistic simplification remain; not a survey or construction standard.
- 1440/768/390 desktop Chromium WebGL viewport checks PASS, exact GLB bytes/hash consumed, orbit/zoom/reset/reopen and close canvas cleanup. reports/browser-corrected/results.json. Viewport emulation is NOT real mobile testing.
- Final producer unit suite303/303 and build PASS: docs/verification/fifty02-heritage/unit-contact-final.log and build-contact-final.log. Existing runtime build has a chunk-size warning. Combined latest-main integration and legacy full lifecycle regressions are outside this producer gate.
- Physical Android, iOS, Safari/WebKit and device performance remain NOT TESTED.
## Interaction
Two synchronized clips OpenClose_Left/Right, frames 0/30/60 at30fps: closed at0s, 85° open at1s, closed at2s. Explicit raw track endpoints, expected angle, fixed hinge positions, central clearance and restored closed pose checked. Real Chromium AnimationMixer pixels differ when open and restore exactly when closed. No Gallery playback UI or physics.
## Provenance
Original deterministic Blender Python meshes and materials; no marketplace assets, external texture or external font. Original art; owner-project reuse authorized; public redistribution license unspecified. No copied heritage site or official certification.
## History
Initial shared validator newline syntax failure retained; corrected only escaping. Actual coplanar joint fixes and temple roof tile bevel optimization documented in docs/verification/fifty02-heritage/corrections.md. Initial changed binaries/previews and failed logs retained. Latest report/hash above governs; historic snapshots are not release assets.
## Reproduce from repository root
Set BLENDER to the existing Blender executable/wrapper and use:
```sh
"$BLENDER" -b -t 2 --python models/straits-shophouse-door/generate.py
node models/straits-shophouse-door/validate.mjs
"$BLENDER" -b -t 2 --python models/straits-shophouse-door/inspect_source.py
node models/straits-shophouse-door/verify_source_edit.mjs
"$BLENDER" -b -t 2 --python models/straits-shophouse-door/render_views.py
MALL_QA_DIR=/tmp/fresh-straits-shophouse-door-qa node scripts/test-straits-shophouse-door.mjs
```
Generation intentionally rebuilds originals; for preserving a manual source edit use generate.py --export-source instead. Browser tests require npm run build first. Use a fresh output directory so previous evidence remains intact.

Animation evidence: reports/animation-proof.json and reports/animation-browser-corrected/results.json. Run MALL_QA_DIR=/tmp/fresh-straits-shophouse-door-animation node scripts/test-straits-shophouse-door-animation.mjs.

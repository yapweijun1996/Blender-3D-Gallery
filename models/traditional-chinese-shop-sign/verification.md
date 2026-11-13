# Traditional Chinese Shop Sign verification
Date: 2026-11-13. Backlog 415.
Local asset gate **PASS**; release/mobile status **NEEDS REVIEW**. No deployment or remote submission.

## Delivered evidence
- Source sources/traditional-chinese-shop-sign.blend reopened with Blender4.0.2, metre units, independent mesh data and finite geometry checked.
- Source-copy component edit +0.2m and material roughness change saved, reopened from edited .blend, exported WITHOUT generator regeneration. Original source SHA unchanged. reports/source.json, source-edit.blend, source-edit.glb and source-edit-proof.json; inspect_source and verify_source_edit logs record material assertion.
- GLB 43740 bytes / 648 triangles within fixed 350000-byte / 7500-triangle budgets. Khronos zero errors/warnings. SHA256 b4078f14488c1a1f255be9bd3c6bea9adec17d976da9c45209b269db2926cf34. reports/assets.json.
- Actual exported GLB studio hero/front/rear/side pixels inspected; all three current Chromium initial viewport screenshots inspected. Recognizable simplified geometry and material separation. Fine Cycles grain, grazing-angle thin silhouettes and stylistic simplification remain; not a survey or construction standard.
- 1440/768/390 desktop Chromium WebGL viewport checks PASS, exact GLB bytes/hash consumed, orbit/zoom/reset/reopen and close canvas cleanup. reports/browser-corrected/results.json. Viewport emulation is NOT real mobile testing.
- Final producer unit suite303/303 and build PASS: docs/verification/fifty02-heritage/unit-contact-final.log and build-contact-final.log. Existing runtime build has a chunk-size warning. Combined latest-main integration and legacy full lifecycle regressions are outside this producer gate.
- Physical Android, iOS, Safari/WebKit and device performance remain NOT TESTED.
## Interaction
Static architectural prop; no artificial runtime animation. Independent editable meshes and materials.
## Provenance
Original deterministic Blender Python meshes and materials; no marketplace assets, external texture or external font. Original geometric vector strokes spell 茶 (tea); no CJK font, logo or brand. Original art; owner-project reuse authorized; public redistribution license unspecified. No copied heritage site or official certification.
## History
Initial shared validator newline syntax failure retained; corrected only escaping. Actual coplanar joint fixes and temple roof tile bevel optimization documented in docs/verification/fifty02-heritage/corrections.md. Initial changed binaries/previews and failed logs retained. Latest report/hash above governs; historic snapshots are not release assets.
## Reproduce from repository root
Set BLENDER to the existing Blender executable/wrapper and use:
```sh
"$BLENDER" -b -t 2 --python models/traditional-chinese-shop-sign/generate.py
node models/traditional-chinese-shop-sign/validate.mjs
"$BLENDER" -b -t 2 --python models/traditional-chinese-shop-sign/inspect_source.py
node models/traditional-chinese-shop-sign/verify_source_edit.mjs
"$BLENDER" -b -t 2 --python models/traditional-chinese-shop-sign/render_views.py
MALL_QA_DIR=/tmp/fresh-traditional-chinese-shop-sign-qa node scripts/test-traditional-chinese-shop-sign.mjs
```
Generation intentionally rebuilds originals; for preserving a manual source edit use generate.py --export-source instead. Browser tests require npm run build first. Use a fresh output directory so previous evidence remains intact.

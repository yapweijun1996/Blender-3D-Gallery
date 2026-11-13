# HDB Rubbish Chute Hopper verification

**Local asset: PASS. Overall: NEEDS REVIEW.** V2.1 item 314; one independent logical model. Physical Android/iOS **NOT TESTED**; combined batch4 ten-model integration **PENDING**. Not release/deployment approval.

## Evidence

- Blender 4.0.2 saved source reopened; 14 independently editable closed/manifold positive-volume mesh objects; metre scale and root datum validated: [source](reports/sources.json).
- Saved-source vertex edit (local X ×0.92) and material roughness change survived re-export without regeneration; original source hash unchanged: [source edit](reports/source-edit-verify.log). Edited fixture is not cataloged.
- GLB 98,416 bytes / 1,832 triangles / 14 primitives / 3 materials; zero images/textures/animations, external URIs, cameras or lights. Khronos zero errors/warnings: [structure](reports/assets.json). Budget 200,000 bytes and 4,000 triangles.
- Dimensions glTF X/Y/Z: 0.7600, 0.8000, 0.4135 m; glTF +Y up, front+Z; Blender +Z up/front−Y. Bottom datum0 verified.
- GLB SHA-256 `60a5478a606135410fc1209f8c8de864f3a5e445fe1c335ec0d40e2d180780b0`.
- Strict desktop Chromium 156.0.8078.4: **3/3** at 1440×900,768×1024,390×844; exact consumed byte count/SHA, HTTP200, WebGL draws, orbit/zoom, pixel-identical reset/reopen, horizontal fit and all unexpected request/console/page errors checked without filtering: [browser](../../docs/verification/hdb-batch04-a/browser-hopper-preview/results.json). Desktop viewport emulation is not Android/iOS hardware.
- Hero/front/rear/side studio renders and actual Gallery initial views at 1440/390width were inspected. Recognizable geometry, clear silhouette, coherent materials; not photorealism or surveyed-installation certification.
- Full existing unit suite **223/223**, production build/catalog/GLB validation PASS: [unit](../../docs/verification/hdb-batch04-a/unit.log), [build](../../docs/verification/hdb-batch04-a/build-metadata.log). Existing Vite chunk-size advisory remains, not hidden.

## Limits and reproduction

Title-only scope permits generic original geometry, not specific as-built HDB equipment. No structural, fire, safety, fitness, hygienic, security or building-code compliance asserted. Source components editable; no added runtime articulation or simulation. Physical mobile/Safari and mobile performance unverified. Public redistribution license unspecified, downloads disabled. No remote push/PR/merge/deploy.

Run Blender 4.0.2 `--background --threads 2 --python-exit-code 1 --python models/hdb-rubbish-chute-hopper/generate.py`; use `-- --export-source --skip-render` for saved-source export. `node models/hdb-rubbish-chute-hopper/validate.mjs`; Blender `inspect_sources.py`; `node models/hdb-rubbish-chute-hopper/verify_source_edit.mjs`. Source inspection writes new fixture/reports, so use an isolated copy when preserving previous evidence. Run `npm test`, `npm run build`, then `MALL_QA_DIR=... node scripts/test-hdb-batch04-a.mjs`; optional HDB_QA_ASSET selects one asset without changing assertions.

First strict browser 15/15 passed but visual review found the stainless material too dark in default Gallery lighting. The already-supported optional per-model previewLighting now uses hemisphere4/directional5, position[4,7,5]. Original metadata-independent GLB SHA is unchanged. All affected3 cases passed again and actual before/after pixels were inspected. Other assets retain defaults. Initial evidence is retained; no errors suppressed. This is preview lighting, not a material/runtime architecture change.

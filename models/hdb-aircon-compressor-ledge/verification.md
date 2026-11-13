# HDB Aircon Compressor Ledge verification

**Local asset: PASS. Overall: NEEDS REVIEW.** V2.1 item 308, one independent asset. Physical Android/iOS remain **NOT TESTED** and the combined ten-model batch gate is **PENDING**. This is not release/deployment approval.

## Executed evidence

- Blender 4.0.2 source reopened; 17 independent closed/manifold mesh objects; metre scale and named editable materials verified: [source report](reports/sources.json).
- Actual saved-source mesh edit and material roughness edit survived GLB export without regenerating geometry: [proof](reports/source-edit-verify.log). Original source SHA stayed unchanged. Edited fixture is not a catalog asset.
- GLB 109,060 bytes, 1,996 triangles, 17 mesh primitives, 3 materials; no external URI, textures, animation, studio camera or light: [structural report](reports/assets.json). Khronos Validator zero errors and warnings. Budget: 150,000 bytes / 3,000 triangles for this simple modular prop.
- glTF X/Y/Z dimensions: 1.8000, 1.1800, 0.8500 m. Blender +Z up, front −Y; glTF +Y up, front +Z. Bottom datum Y=0 verified.
- SHA-256: `3e056b955c46a213f3dbae548545744ba3b0cdff73686950fdbbf98b06ad7d65`.
- Final strict browser: **3/3** at 1440×900,768×1024,390×844 in desktop Chromium 156.0.8078.4. Actual consumed GLB bytes/SHA, HTTP200, WebGL draws, orbit, zoom, exact reset, close/reopen, horizontal fit and all unexpected request/console/page errors checked. No filtering or retry-to-green: [final15-case evidence](../../docs/verification/hdb-batch03-b/browser-contact-final/results.json).
- Four rendered views (hero/front/rear/side) inspected, plus actual Gallery initial views at desktop and390width. Geometry, silhouette and material rendering are recognizable and coherent. This is visual inspection, not engineering certification.
- Full existing unit suite **165/165**, production build and catalog/Khronos checks passed: [unit log](../../docs/verification/hdb-batch03-b/unit-contact-final.log), [build log](../../docs/verification/hdb-batch03-b/build-contact-final.log). The existing chunk-size advisory remains; tests were not weakened.

## Coverage and use limits

Generic original residential geometry, not measured as-built HDB equipment. No load, wind, drainage, electrical, security, fire or building-code performance claimed. Named movable parts are independently editable in source, not new runtime UI controls. Physical mobile devices, Safari/WebKit, touch hardware and mobile performance are unverified. Owner-project reuse is allowed; public redistribution terms unspecified and downloads remain disabled. No push, PR, merge or deployment by this preparation.

Reproduce: run generate.py in Blender4.0.2; node validate.mjs; Blender inspect_sources.py; node verify_source_edit.mjs; npm test; npm run build; MALL_QA_DIR=... node scripts/test-hdb-batch03-b.mjs. Final batch owner must rerun combined integration checks.

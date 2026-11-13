# Hawker Stall Stainless Counter verification

**Local asset: PASS. Overall: NEEDS REVIEW.** V2.1 item 363, one independent logical asset. Physical Android/iOS **NOT TESTED**; combined ten-model batch5 quality gate **PENDING**. Not deployment approval.

## Executed evidence

- Blender 4.0.2 source reopened; 15 individually editable closed/manifold positive-volume mesh objects; unit scale 1 metre and root datum checked: [source report](reports/sources.json).
- A real saved-source mesh-vertex edit and material roughness edit survive GLB re-export without regeneration. Original source hash unchanged: [proof](reports/source-edit-verify.log). Edited fixtures are not cataloged.
- GLB **121,732 bytes / 2,324 triangles**, 15 primitives, 2 materials; Khronos zero errors/warnings; no texture/image, external URI, animation, camera or light: [structure](reports/assets.json). Budget 250,000 bytes / 5,000 triangles.
- glTF X/Y/Z dimensions: 2.2000, 1.0200, 0.7500 m. Blender +Z up/front−Y; glTF +Y up/front+Z; lower datum 0 verified.
- Exact GLB SHA-256: `433e4abfbe60e3e1c9c5a24254054beb4aeda1669bbcf67253a1d30c9899ab8d`.
- Desktop Chromium 156.0.8078.4: **3/3** at 1440×900,768×1024,390×844. Tests assert exact consumed bytes/SHA, HTTP200, WebGL drawing, orbit/zoom, exact reset/reopen, no horizontal overflow and all unexpected request/console/page errors unfiltered: [final 15-case browser evidence](../../docs/verification/batch05-a/browser-final/results.json). No retry-to-green.
- Hero/front/rear/side studio images inspected, plus actual Gallery initial images at desktop/390width. Hood additionally has an inspected underside render. Geometry remains simple, recognizable and proportioned; no claim of photorealism or as-built authenticity.
- Full existing unit suite **230/230**, production build and catalog/GLB validation passed: [unit](../../docs/verification/batch05-a/unit.log), [build](../../docs/verification/batch05-a/build-metadata.log). Existing bundle-size advisory remains documented, not suppressed.

## Limits

Generic original modules based on title-only scope. No structural, load, fire, ventilation, food-hygiene, access, electrical or building-code compliance claimed. Components are editable in source; no runtime opening, airflow, signage interaction or lighting control implemented. Physical Android/iOS, Safari/WebKit and mobile hardware performance remain untested. Owner-project reuse allowed; public redistribution terms unspecified and downloads disabled. No push/PR/merge/deployment by this worker.

Reproduce with Blender 4.0.2 generate.py and inspect_sources.py; node validate.mjs and verify_source_edit.mjs; npm test; npm run build; MALL_QA_DIR=... node scripts/test-batch05-a.mjs. Source inspection writes fixture/reports; use an isolated copy to preserve historic evidence.

## Modular placement check

Item361 shutter is a service-opening module, not a renamed full-height mall shutter. Place its glTF root at `[0,0.9,-0.48]` relative to item363 counter. Counter worktop and shutter lower datum both Y=0.9m; all 450 cross-asset mesh pairs checked with 0 penetrations. [Assembly evidence](../hawker-stall-roller-shutter/reports/counter-assembly.json). This demonstrates geometric composability, not installation or fire/food-safety clearance certification.

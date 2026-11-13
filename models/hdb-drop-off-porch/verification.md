# HDB Drop-Off Porch verification

**Local asset: PASS. Overall: NEEDS REVIEW.** V2.1 item 320, one independent logical asset. Physical Android/iOS **NOT TESTED**; combined ten-model batch5 quality gate **PENDING**. Not deployment approval.

## Executed evidence

- Blender 4.0.2 source reopened; 14 individually editable closed/manifold positive-volume mesh objects; unit scale 1 metre and root datum checked: [source report](reports/sources.json).
- A real saved-source mesh-vertex edit and material roughness edit survive GLB re-export without regeneration. Original source hash unchanged: [proof](reports/source-edit-verify.log). Edited fixtures are not cataloged.
- GLB **80,000 bytes / 1,412 triangles**, 14 primitives, 6 materials; Khronos zero errors/warnings; no texture/image, external URI, animation, camera or light: [structure](reports/assets.json). Budget 250,000 bytes / 5,000 triangles.
- glTF X/Y/Z dimensions: 6.0950, 3.2400, 4.5450 m. Blender +Z up/front−Y; glTF +Y up/front+Z; lower datum 0 verified.
- Exact GLB SHA-256: `621060a1d30f07c65cc45f372c623fc42d7092196ed744e4bcbe026446d6bdc0`.
- Desktop Chromium 156.0.8078.4: **3/3** at 1440×900,768×1024,390×844. Tests assert exact consumed bytes/SHA, HTTP200, WebGL drawing, orbit/zoom, exact reset/reopen, no horizontal overflow and all unexpected request/console/page errors unfiltered: [final 15-case browser evidence](../../docs/verification/batch05-a/browser-final/results.json). No retry-to-green.
- Hero/front/rear/side studio images inspected, plus actual Gallery initial images at desktop/390width. Hood additionally has an inspected underside render. Geometry remains simple, recognizable and proportioned; no claim of photorealism or as-built authenticity.
- Full existing unit suite **230/230**, production build and catalog/GLB validation passed: [unit](../../docs/verification/batch05-a/unit.log), [build](../../docs/verification/batch05-a/build-metadata.log). Existing bundle-size advisory remains documented, not suppressed.

## Limits

Generic original modules based on title-only scope. No structural, load, fire, ventilation, food-hygiene, access, electrical or building-code compliance claimed. Components are editable in source; no runtime opening, airflow, signage interaction or lighting control implemented. Physical Android/iOS, Safari/WebKit and mobile hardware performance remain untested. Owner-project reuse allowed; public redistribution terms unspecified and downloads disabled. No push/PR/merge/deployment by this worker.

Reproduce with Blender 4.0.2 generate.py and inspect_sources.py; node validate.mjs and verify_source_edit.mjs; npm test; npm run build; MALL_QA_DIR=... node scripts/test-batch05-a.mjs. Source inspection writes fixture/reports; use an isolated copy to preserve historic evidence.

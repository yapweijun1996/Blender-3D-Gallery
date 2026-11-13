# Kopitiam Toast Display verification

**Local asset: PASS. Overall: NEEDS REVIEW.** V2.1 item 373. One logical independent asset. Physical Android/iOS NOT TESTED; combined ten-model batch6 gate PENDING. No publication approval.

## Executed evidence

- Blender 4.0.2: 38 independently editable closed, manifold, positive-volume meshes; metric units and root datum verified. [Source report](reports/sources.json).
- Real saved source mesh vertex and material roughness edits survive GLB export without regeneration; original source hash unchanged. [Source-edit proof](reports/source-edit-verify.log).
- GLB 222,880 bytes, 4,104 triangles; 38 primitives. Khronos zero errors/warnings. No external resources, textures, animations, cameras or lights. [Structure](reports/assets.json).
- Fixed budget: 250,000 bytes and 5,000 triangles. GLB X/Y/Z dimensions 0.580000, 0.457500, 0.340000 metres. Blender +Z up/front -Y; GLB +Y up/front +Z.
- SHA256: `4cead72ba00142bf81a9ce6f78953d607962691ef7d66c21bc94ff4853c4ac9b`.
- Hero/front/rear/side rendered pixels inspected. Original simple geometry, not a photorealism or official authenticity claim.
- Existing unit suite 230/230 and build/catalog validation PASS: [units](../../docs/verification/batch06-b/unit.log), [build](../../docs/verification/batch06-b/build.log). Existing bundle-size advisory retained.

## Limitations

Generic original interpretation of title-only backlog. No surveyed dimensions or structural, electrical, fire, food-hygiene, thermal or load certification. Visual props only, not functional equipment; source parts are editable, not browser-operated. Physical Android/iOS, Safari/WebKit and hardware performance untested. Public redistribution terms unspecified; downloads disabled. No remote push, PR, merge or deployment by this worker.

Reproduce with Blender generate.py and inspect_sources.py; node validate.mjs and verify_source_edit.mjs; npm test; npm run build; MALL_QA_DIR=... node scripts/test-batch06-b.mjs. Source inspector writes fixed paths; run in an isolated copy to preserve historical evidence.

## Browser and actual pixel review

Desktop Chromium 156.0.8078.4: initial strict 15/15 across five assets at 1440×900, 768×1024 and 390×844. Exact consumed GLB bytes/SHA, HTTP200, real WebGL draws, orbit/zoom, pixel-identical reset/reopen, no horizontal overflow and unfiltered request/console/page errors asserted. [Initial results](../../docs/verification/batch06-b/browser-final/results.json).

Actual initial desktop and 390-width screenshots inspected for every asset. Kettle and griddle metal were too dark despite functional passes. Approved existing per-model previewLighting fields were set to hemisphere4/key5 at [4,7,5], leaving geometry and material data unchanged. Affected six cases rerun once, 6/6 PASS; actual updated screenshots inspected. Other three unchanged. [Affected final results](../../docs/verification/batch06-b/browser-metal-preview/results.json). Initial screenshots/evidence retained, no claim that a second full15 ran. Final 20 studio views inspected, plus before/after Gallery pixels.

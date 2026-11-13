# Tactile Paving Tile verification

**Local asset: PASS. Overall: NEEDS REVIEW.** V2.1 item 394, one independent logical asset. Physical Android/iOS and WebKit NOT TESTED. Combined ten-model batch8 gate PENDING. Not deployment approval.

## Executed evidence

- Blender 4.0.2 source reopened: 26 independently editable closed/manifold positive-volume meshes, metre scale and root datum verified. [Source](reports/sources.json).
- A real saved source mesh vertex edit and material roughness edit survive GLB export without regeneration; original source unchanged. [Proof](reports/source-edit-verify.log).
- GLB 80,924 bytes / 1,608 triangles / 26 primitives. Khronos 0 errors and 0 warnings; no external URI, textures, animation, camera or lights. [Structure](reports/assets.json).
- Preassigned complexity budget 150,000 bytes / 2,500 triangles. No budget relaxation.
- glTF X/Y/Z dimensions 0.300000, 0.035000, 0.300000 metres. Blender +Z up/front -Y; glTF +Y up/front +Z.
- SHA256 `b35ac4c839ca042549862082029667b2c51e4d06f90909cf3b63644b294285ff`.
- Hero/front/rear/side rendered pixels inspected. Geometry is an original illustrative design, not a surveyed or certified product.
- Existing unit suite 230/230 and build/catalog validation PASS. [Units](../../docs/verification/batch08-b/unit.log), [build](../../docs/verification/batch08-b/build.log). Existing bundle-size advisory retained.

## Limitations

No hydraulic, drainage-flow, strength/load, engineering, road or tactile/accessibility compliance claimed. Components editable in Blender, not runtime simulation or interaction. Physical Android/iOS, Safari/WebKit and mobile hardware performance untested. Owner-project reuse permitted; public redistribution terms unspecified; downloads disabled. No remote actions by this worker.

Reproduce using Blender generate.py/inspect_sources.py, node validate.mjs/verify_source_edit.mjs, npm test/build and scripts/test-batch08-b.mjs. Source inspector writes fixed report/fixture paths; use isolated copy to preserve historical evidence.

## Browser and actual pixel gate

Desktop Chromium 156.0.8078.4: strict15/15 across all five assets at1440×900,768×1024,390×844. Exact consumed GLB bytes/SHA, HTTP200, real WebGL draws, orbit/zoom, exact reset/reopen pixels, no horizontal overflow and unfiltered unexpected request/console/page errors asserted. [Results](../../docs/verification/batch08-b/browser-final/results.json). No retry-to-green or filtered errors.

Actual Gallery preflight inspected before final suite; final20 studio views and actual10 desktop/390-width initial screenshots inspected. Existing optional previewLighting fields used for presentation;394 also uses a top-biased camera to show studs. Old assets unchanged. Physical mobile/WebKit remain untested.

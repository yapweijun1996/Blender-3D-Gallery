# Item 428 verification

## Result

**Local model/source/visual/Gallery checks: PASS. Overall: NEEDS REVIEW**, solely because physical Android and iOS testing is unavailable. Desktop Chromium viewport emulation is not physical mobile-device coverage. No publication, deployment or structural/safety/code compliance is claimed.

| Gate | Evidence/result |
| --- | --- |
| Source reopening | `reports/sources.json`: Blender 4.0.2, metre scale, 57 independent closed manifold meshes, 43 real railing source meshes, eight tiles, no library links, packed image |
| Isolated source edit | `reports/source-edit.json`: copied source/generator with no sibling inputs exports all assembled parts; fascia geometry/material changes, other 64 material primitives and other materials unchanged, original source preserved |
| Khronos glTF Validator | `reports/assets.json`: 0 errors, 0 warnings, validator 2.0.0-dev.3.10 |
| Budgets | 486,156 GLB bytes; 4,940 triangles; 9,608 vertices; 65 primitives; 11 materials; one embedded 512px image; no animation |
| Bounds and origin | 2.16 × 1.371 × 1.22 m; underside at local Y=0, finished deck and rail seating at Y=0.25 |
| Reused geometry | All 3,236 original 006 railing triangles match transformed original export; 421 material definitions and image bytes match; input hashes remain unchanged |
| Assembly | `reports/assemblies.json`: single/three-bay actual GLB layouts; unique joint posts; two outer end closures; adjoining slab edges without overlap; rail seats at finished deck; post plates fit deck/end-closure footprint |
| Studio views | Five actual-GLB PNG/WebP pairs reviewed: primary, front, rear, underside and three-bay assembly. No missing components, double posts, floating rail or clipped silhouette observed |
| Focused units | 6/6, `reports/focused-tests.txt` |
| Full units | 160/160, `reports/unit-tests.txt` |
| Build | PASS, `reports/build.txt`; existing Vite large-chunk advisory remains, not a build error |
| Strict Gallery | 3/3 viewports: 1440×900, 768×1024, 390×844. Exact served/consumed GLB SHA and HTTP 200, real draw calls, orbit, zoom, exact reset, further underside orbit, close/exact reopen, no horizontal overflow, download hidden; no requestfailed/console/page errors and no abort filtering. `reports/browser/results.json` |
| Transparency | `reports/glass/results.json` and original/opaque/hidden PNGs: original alpha glass visibly shows checker; opaque hides it; hidden removes tint. Exact shipped GLB SHA, HTTP 200, no errors |
| Library regression | 9/9 existing cases, `reports/library/results.json` and `reports/library-tests.txt` |
| Physical Android / iOS | NOT TESTED, NEEDS REVIEW |

Verified export SHA-256: `5d5247640c2a99ab414507cacf2928e954621f3248dc6f42ad90257ee98fbe62`.

## Visual review

All five studio images, all three initial Gallery viewports, mobile full-page layout, all nine orbit/zoom/underside views and three glass diagnostic controls were inspected. Initial/reset/reopen pixel hashes are identical at each viewport. All source parts are present; tiles stay visible through glass; end closures and the inset underside are legible. The browser `rear` filenames denote the additional vertical-orbit/underside step, not a separate rear-facing camera preset. The source studio `rear.png` is the actual rear view.

## Preservation and limits

Only one new catalog collection/asset is appended. Catalog schema/order and previous entries, prior assets, reports and application behavior are preserved. This model uses only the already-supported preview-camera option. Original public-download and license restrictions remain unchanged. The source mesh edit is a separate disposable fixture, not a change to the committed source. No remotely published changes or deployments were made.

The model supplies a visual architectural silhouette, not an engineered support system, live physics, railing safety calculation, attachment detail, accessibility/slip/fire rating or Singapore/Malaysia regulatory certification.

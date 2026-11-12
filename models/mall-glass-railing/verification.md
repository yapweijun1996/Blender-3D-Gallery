# Glass railing verification · 2026-11-12

## Gate outcome

**Overall NEEDS REVIEW. Strict gallery E2E: FAIL (8/9 passed). No deployment performed.**

| Asset | Source / GLB / visual checks | Strict gallery cases | Outcome within tested scope |
| --- | --- | --- | --- |
| Post | PASS | 3/3 PASS | PASS |
| 1 m bay | PASS | 3/3 PASS | PASS |
| 2 m bay | PASS | 2/3 PASS, 390×844 FAIL | NEEDS REVIEW |

Android and iOS browsers are **NOT TESTED** for every asset. All browser evidence is desktop Chromium 156.0.8078.4 on Ubuntu ARM64 with software WebGL, including tablet/mobile-sized viewport emulation. It is not evidence of physical mobile-device support. Interaction checks cover the existing viewer's orbit, zoom and reset, not movable asset components.

## Executed evidence

- Main baseline: `b7421d284b503ff923508fc3046b2193108f503a`.
- Blender 4.0.2 ARM64, Node 22.23.3, Three.js 0.187.0, Playwright 1.64.1, Khronos validator 2.0.0-dev.3.10.
- `reports/assets.json`: all three GLBs have zero Khronos errors/warnings, self-contained buffers, no external images, no cameras/lights/animations, metre scale and floor origin. Budgets: at most 500 KB, 12,000 triangles and 16 primitives each.
- `reports/sources.json`: all saved Blender files reopened successfully, with 16/43/43 editable parts; source hashes recorded.
- `reports/source-edit.json`: an isolated saved 1 m source changed glass alpha from 0.28 to 0.44. Re-export preserved all geometry, nodes and other material/asset data. Shipped sources/exports were not modified by this test.
- `reports/assembly.json`: real exported connected pieces tested in repeated and mixed right-angle assemblies. 3,507 and 5,926 intermodule piece pairs checked; maximum connector error 2.29e-8 m. Maximum AABB penetration 0.500009 mm is the designed receiver gasket contact, below 0.51 mm tolerance.
- `npm test`: **119/119 PASS**. `npm run build`: **PASS**, including all catalog GLBs with zero validation errors/warnings. Existing large-JS-chunk warning remains.
- `npm run test:library`: **9/9 PASS**.
- `reports/browser.json`: one fixed nine-case strict pass over three assets at 1440×900, 768×1024 and 390×844. All consumed the exact committed GLB bytes/SHA-256, had HTTP 200 responses, WebGL draw calls, orbit/zoom/reset effects, disabled downloads and no horizontal overflow.
- **Failure retained:** the 2 m bay at 390×844 also emitted `net::ERR_ABORTED` for `assets/mall-glass-railing-2m-H2JXjHCu.glb`. Therefore its strict case failed despite successful rendering and the other checks. No request failure, including ERR_ABORTED, was filtered. No acceptance rerun was used to obtain a green result. Root cause is unresolved; this does not establish that prior intermittent model-request failures are fixed.
- `reports/glass-material.json` and `reports/screenshots/glass-comparison.webp`: supplemental unchanged-GLB Three.js diagnostic **PASS**. HTTP 200 and exact source SHA verified; actual material opacity 0.28, transparent=true, depthWrite=false. A checker behind the panel remains visibly tinted in the original, disappears in the opaque control and is untinted in the hidden control. No console/page/request errors. This is separate from and does not override the failed gallery gate.

## Personal visual inspection

The authoring worker inspected actual pixels from all three source perspective/front/rear views, the imported-GLB right-angle assembly, all nine initial gallery screenshots, and the glass original/opaque/hidden comparison. The glass is visibly present and transparent, not vanished or opaque; proportions, feet, posts, clamps, rail continuity and the orthogonal join are readable without obvious duplicated joints. Screenshot evidence is in `reports/screenshots/`. A second reviewer independently inspected the 2 m 390-pixel gallery view and assembled turn.

## Corrections and limitations

- The first catalog insertion broke the existing floor-sign-to-queue adjacency test. Only the new block was moved before the service-desk collection; existing tests and entries were not altered. The final full suite passed.
- The first assembly preview retained imported quaternion rotation mode, so its turned infills did not rotate. The preview renderer now explicitly selects Euler mode; the corrected imported-GLB assembly was visually reviewed.
- The initial perfectly horizontal front camera showed the studio-floor edge. It was raised for clean front-elevated views, then rerendered and inspected.
- The first supplemental material harness timed out after opening the raw unbuilt application document. It was corrected to use a blank same-origin fixture, then passed. This did not change production UI, assets or the failed strict gallery result.
- Alpha glass is a compatibility approximation, not optical simulation. No load tests, impact safety, structural validation, regulatory certification, real touch hardware, Android Chrome or iOS Safari verification occurred.
- This local commit is one logical kit toward the requested ten-model batch. No push, PR, merge, publishing or deployment was performed.

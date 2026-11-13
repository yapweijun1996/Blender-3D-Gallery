# 433 verification: local asset PASS; initial-base browser FAIL; overall NEEDS REVIEW

2026-11-12. Prepared item **4/10 of the second batch**, not released and not final merged-base integration.

## Base, preservation and limits

- Isolated local clone at 3b83acb7e996a7c8324ac5f2a69e21eaa78a4749, preserving prepared 430–432. Old main is b7421d284b503ff923508fc3046b2193108f503a.
- git ls-remote immediately before final initial-base gates still returned that old main. PR #12 integration was not incorporated. Main must actually advance before final merged-base integration.
- Changes are only the independent 433 asset, append-only catalog registration, focused tests/browser script and evidence. No app, viewer, loader or schema changes. Only the pre-existing previewRotationY field is used.
- All inherited catalog assets and old tracked files except the appended catalog are unchanged. Exact counts and base in reports/preservation.json.
- No merge/history rewrite, remote push, PR action or deployment. Physical Android/iOS **NOT TESTED**. Final merged-base integration **PENDING / NEEDS REVIEW**.

## Asset and source: PASS

| Gate | Evidence |
| --- | --- |
| GLB | 315,348 bytes; SHA-256 e58dcb5fac5fc63d84936c34a3df2fd3085ade3c773fec7095e73612c8b13b03 |
| Geometry | 6,004 triangles; 11,712 vertices; 35 independent mesh primitives; six materials |
| Dependencies | Zero textures, animation clips, external fonts/models/logos; original EXIT letter strokes |
| Khronos | 2.0.0-dev.3.10; zero errors and warnings |
| Mounting | Floor-centre origin, 0.96 × 2.10 m opening, 0.14 m frame depth |
| Scale | Frame 1.10 × 2.18 m; 0.95 × 2.083 × 0.05 m leaf; 12 mm floor and 5 mm side/head gaps |
| Push bar | Independent 0.79 m bar at height 1.03 m; 18 mm source depression; exact 67.5 mm remaining leaf gap |
| Collision sweep | 101 source angles 0–100° × 3 press positions, 7,272 conservative moving-part/frame checks; zero collisions |
| Closer | Two actual 0.28 m source links retain anchor/elbow lengths across all pose samples |
| Placement envelope | Maximum sampled hardware front reach 1.008 m; documented 1.10 m visual scene clearance |
| Source proof | Delivered Blender source reopened, saved isolated 85°/18 mm edit, reopened, exported; all 35 mesh coordinate arrays and frame transforms preserved |
| Source integrity | Delivered .blend SHA unchanged after proof; edited GLB Khronos 0/0 |
| Previews | Six PNG/WebP views; all WebPs under 150 KiB; studio and actual browser pixels inspected |
| Units | Focused 6/6; full 135/135 PASS |

The collision check uses conservative oriented bounds of actual source meshes and excludes intentionally joined hinge/closer bearings. It is sampled visual model testing, **not** certified hardware engineering, fire resistance, building-code or evacuation-safety validation. Source poses do **not** add runtime door UI.

An initial source-check development run used a mistaken 69 mm bar-gap expectation. The exact geometry arithmetic is 128 − 17.5 − 18 − 25 = **67.5 mm**. The assertion was corrected to an exact 67.5 mm check, not removed, and the initial log is retained as source-inspect-initial.log. No model geometry, collision rule or browser error filter was weakened. Front studio preview initially showed the floor grazing the orthographic horizon; the floor is now hidden for that front-only studio view. Exported geometry was unchanged.

## Initial-base application gates

- npm test: **135/135 PASS**.
- npm run build: **PASS**, all catalog assets Khronos 0/0. Existing Vite chunk-size warning retained.
- npm run test:library: **9/9 PASS**.
- One strict, unfiltered Chromium 156.0.8078.4 run: **0/3 PASS**, with 1440×900, 768×1024 and 390×844 tested once. No retry to green.

All three viewports consumed the exact exported GLB SHA and 315,348 bytes. Observed GLB HTTP responses were 200. All had real draw calls, distinct orbit/zoom pixels, exact reset and reopen pixels, three same-page lifecycle cycles, stopped rendering after close, restored card focus and no horizontal overflow.

The strict gate correctly failed on retained net::ERR_ABORTED requests from the unchanged old-base loading/lifecycle behavior: **3 at 1440, 1 at 768, 4 at 390**. These are recorded unfiltered in reports/browser-initial-base/results.json. The result is **not a clean browser PASS**, even though rendering and controls completed. No unmerged loader code was copied and no competing fix was added.

Evidence: reports/gate-exit-codes.json, unit.log, build.log, browser.log, library.log, built-artifact.json, full screenshots and browser results. Studio sheet: reports/studio-contact-sheet.webp; actual browser page sheet: reports/browser-contact-sheet.webp.

## Review conclusion

The original asset is locally validated, recognizable and independently editable; source quality is PASS. In studio and browser pixels, the red leaf, contrasting frame, original EXIT plaque, push bar, kick plate, hinges and closer remain legible with no clipped model at the tested widths. Open source pose has a visible clear opening and connected closer links. Gallery download remains disabled.

Overall **NEEDS REVIEW** because initial-base strict browser lifecycle is not clean, final merged-base integration is pending, and physical Android/iOS are not tested. Re-evaluate final app gates only on the actual merged main and approved final combined batch. Do not count this as released or ready to merge.


Independent parent review inspected the hero, open pose and actual 390 px initial browser pixels and accepted local visual quality. No further refinement was requested.

Plain-text console logs normalize trailing whitespace only; no errors or events were removed. Browser JSON and screenshots remain unfiltered.

> Final combined review (2026-11-12): configured underside presentation and strict Gallery checks **PASS 3/3** on the final ten-type batch. See [independent batch verification](../../docs/verification/mall-batch-10.md) and [fresh results](../../docs/verification/mall-batch-10/browser-ceiling-panel.json). This supersedes only the historical presentation limitation below; overall remains **NEEDS REVIEW** and native Android/iOS remain **NOT TESTED**.

> Update: the initial rear/dark-underside presentation described below is the original baseline. Optional camera/light configuration now addresses it; see [current viewer verification](../../docs/verification/preview-config.md). Original observations are retained.

# Mall Ceiling Panel verification, 2026-11-12

## Result

**Overall: NEEDS REVIEW.** The source/export, actual-export assembly, build and desktop browser checks pass. The existing gallery's elevated initial camera shows the ceiling rear, not the decorative underside. Orbit exposes the underside, but the existing upper-biased lighting makes it dark. These two visual limitations require review and are **not** disguised as a complete visual pass. No viewer behavior, UI, global camera or metadata schema was changed.

**Physical Android and iOS: NOT TESTED.** Narrow desktop viewports do not establish native browser, mobile GPU, device performance or touch coverage. Nothing was remotely pushed, published or deployed.

## Measured artifact

- GLB: 147,100 bytes; 1,724 triangles; 3,312 vertices; 29 mesh primitives; 5 exported materials (4 named source materials plus an exporter primitive variant).
- One embedded original 256 × 256 PNG. No external resource URLs, cameras, lights, animation or decoder dependency.
- GLB bounds: 1.2 × 0.36 × 1.2 m in glTF X/Y/Z. Visible grid underside Y=0; panel underside Y=0.008; panel top Y=0.024.
- GLB SHA-256: `40f7e02cc5f4db5fa3556ddda90c69ea128c98848707106433c25d1018b1d7ef`.
- Source SHA-256: `61dc761bb83dc51d914f8cc3a6ec82de8408c3720dad7a869c248af46ba49163`.
- WebP preview sizes: 6.4–11.2 KiB. Full-resolution PNGs are archival render evidence, not the served card images.

## Executed checks

| Check | Result | Evidence |
| --- | --- | --- |
| Khronos glTF Validator 2.0.0-dev.3.10 | PASS, 0 errors / 0 warnings | reports/assets.json |
| Metres, +Z→+Y, 25 named mesh components, bounds, underside surface rays | PASS | validate.mjs, reports/assets.json |
| Source reopen, 25 positive-volume closed manifold meshes, 4 connectors, packed texture | PASS | inspect_sources.py, reports/sources.json |
| Saved-source mesh/material edit and re-export | PASS | reports/source-edit.json |
| Actual GLB 3×3 repeat + alternating quarter-turn layouts | PASS, 60 panel gaps and 12 connector seams per layout; no measurable module AABB overlap | reports/assembly.json |
| Full Node unit suite | PASS, 127/127 | reports/unit-final.log |
| Production asset validation + Vite build | PASS | reports/build-final.log |
| Strict desktop Chromium direct viewer | PASS, 3/3 at 1440×900, 768×1024, 390×844 | reports/browser.json |
| Library regression suite | PASS, 9/9 groups | reports/library.json, reports/library-final.log |
| Multi-angle actual-GLB render pixel review | PASS | previews/*.png and *.webp |
| Initial viewer side / underside viewer lighting | NEEDS REVIEW | reports/browser/*-initial.png, *-underside.png |
| Native Android / iOS | NOT TESTED | No physical device available |

The build retains the pre-existing shared-chunk size warning. The Blender distribution logs unavailable optional Draco support; this asset does not request Draco and uses a self-contained, uncompressed GLB. Neither warning is suppressed.

### Strict browser evidence

Desktop Chromium 156.0.8078.4 on Ubuntu/Linux ARM64, Node v22.23.3, headless SwiftShader. Every viewport checks:

- The actual consumed response bytes match the shipped 147,100-byte GLB and exact SHA above.
- GLB HTTP status 200; every request failure, console error, page error and HTTP error is collected, with **no ERR_ABORTED filtering**.
- WebGL draw calls occurred, title matched and public download remained hidden.
- Orbit, zoom, reset and an additional underside orbit change the rendered canvas.
- Document horizontal overflow is absent.

The lower viewpoint's canvas is dark because the existing global directional/hemisphere lighting primarily illuminates upper surfaces. Do not confuse different screenshot hashes or successful draw calls with visual acceptance.

The raw library regression report preserves an inherited hardcoded “macOS headless / SwiftShader” label from the unchanged harness. It was actually run on Linux ARM64; `reports/environment.json` records the real process environment. The library suite is not evidence of macOS or physical-device execution.

### Source-edit proof

The test reopened the shipped source, made an isolated copy, lowered only PANEL_1 underside vertices by 2 mm, changed shared underside roughness 0.85→0.65, saved it and invoked `--export-source --skip-render`. The resulting GLB validates with 0 errors / 0 warnings; other component bounds and embedded texture remain unchanged. Edited GLB SHA-256: `14ee8f404bedba9531d8b2e8916ca6469ff7664aefab1c2ab3b46cd69d99af69`. Shipped source/export hashes remain unchanged.

### Human-readable visual inspection

The actual-export studio previews show four distinct recessed panels, consistent grid width, thin vertical suspension pieces, and an uninterrupted repeated 3×3 grid. Rear and low-edge views expose the panel depth and suspension arrangement. No clipped module bounds, detached visible pieces or obvious z-fighting were observed in these views.

Initial gallery screenshots at desktop and narrow width show all four panels, grid and hangers without cropping, but from the rear. The underside orbit screenshots show the correct lower side and grid, but substantially too dark for a final presentation-quality signoff.

## Scope and preservation

One selected logical model, backlog item 422. No electrical light module, architectural certification or fabrication claim. Catalog changes are one insertion only; all pre-existing catalog bytes, model files, test evidence and disabled-download rights remain untouched. No unrelated refactor or weakened test. Local work only; no remote push, PR, merge or deployment.

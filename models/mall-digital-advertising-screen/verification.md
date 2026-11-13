# Verification · Mall Digital Advertising Screen · 437

Prepared locally on initial base 6fe88bef61786c1627798fea377d98b0c10c2fc5. This is not a final merged-base or release pass. No push, PR, merge or deployment performed.

## Asset and source

- Exact GLB SHA-256: b7240c3464221e18caa9897dcc6a67270a7c6cafee04e81030f462ca9f14a757.
- 665,728 bytes; 5,116 triangles; 10,312 vertices; 17 independent mesh primitives; 5 materials; 1 embedded 1024 × 576 PNG; zero animations.
- Khronos Validator 2.0.0-dev.3.10: **0 errors, 0 warnings**.
- Dimensions measured from GLB: 1.28 × 0.755 × 0.085 m. Active image 1.20 × 0.675 m, 16:9. Wall plane glTF Z=0; front +Z.
- Actual delivered Blender 4.0.2 source reopened. All 17 mesh objects have positive volume, no nonmanifold edges, no degenerate faces, unit scales, independent named editing modules.
- One source image is packed. Embedded PNG decodes and matches source PNG RGB pixels exactly. Editable original artwork scene is retained but not exported.
- Genuine source edit: swapped actual screen image red/blue pixels and reduced emission 0.75 to 0.5; saved, reopened and re-exported. Edited embedded-image SHA changed; all 17 mesh coordinates/indices and transforms unchanged; only screen material changed; shipped source unchanged; edited GLB Khronos 0/0.
- Six PNG/WebP views: front hero, straight front, side, rear, mount, wall context. Context wall is not exported.
- Actual rendered pixels inspected: landscape silhouette, legible FRESH FINDS title, original geometric artwork, dark bezel, clear rear service cover, wall mounting rails and ventilation grilles. Actual browser pixels inspected at all three viewports. Screen content is readable, material remains emissive rather than blank; no texture loss or clipping observed.
- Existing portrait lightbox and directory kiosk generators and metadata inspected before registration. This landscape wall-mounted screen is not an equivalent or duplicate.

## Local prepared-base gates

- Focused contracts: **6/6 passed**.
- Full unit suite: **159/159 passed**.
- Production build: **passed**, including catalog asset validation. Existing bundle-size warning remains.
- Library browser suite: **9/9 passed**.
- Strict viewer, one fixed pass only, Chromium 156.0.8078.4 desktop with viewport emulation:
  - 1440 × 900: **FAIL**, two retained unfiltered GET GLB net::ERR_ABORTED entries.
  - 768 × 1024: **FAIL**, two retained unfiltered GET GLB net::ERR_ABORTED entries.
  - 390 × 844: **PASS**, no request/console/page errors.
- All three verified exact consumed SHA/bytes, HTTP 200 GLB responses, rendering, orbit, zoom, pixel-exact reset and reopen, three repeated lifecycle cycles, stop-rendering on close, restored card focus, hidden downloads, and no horizontal overflow.
- No retry, error filtering, loader fix, app/schema/UI change or first-batch implementation copy. These old-loader failures are preserved as failures, not waived or represented as a clean strict-browser pass.

## Preservation and limits

Before final gates, upstream main was b7421d284b503ff923508fc3046b2193108f503a and PR 12 head was 04d31c694520a0935a6c0e65b737bd91f43a8bc6. No unmerged first-batch implementation was copied.

Prior catalog text/entries and all existing tracked asset bytes, including prepared items 430–436, remain unchanged. Only one catalog collection was appended; original rights retained and downloadable=false.

**Physical Android/iOS NOT TESTED. Final merged-base integration PENDING.** This prepared asset must be rechecked on the eventual merged base.

Development validation caught a duplicate texture reference from Blender and an over-budget first grille export. The exporter now deduplicates identical texture references and vent ribs use a one-segment bevel. Final source, renders and all final gates above use that corrected asset. Tests were not weakened.

Evidence: reports/assets.json, geometry.json, sources.json, source-edit.json, image-decode.json, preservation.json, unit-focused.log, unit-full.log, build.log, browser.log, browser/results.json, library.log, and upstream-before-gates.txt.

# Item 440 verification

**Local asset: PASS. Overall: NEEDS REVIEW**, physical Android and iOS NOT TESTED; future batch 03 aggregate integration pending.

Base: main `959fbc773399478e2bfc387a33a543f66be00372`. Exact selected V2.1 source title: 500 Models Master Production Backlog V2.1, dated 2026-11-12, version `ebd4764f267c486e9f2d66517932a92b037315a8aec41405383125cf5f6c502e`, item 440 Mall Retail Pop-Up Cart. No new logical variants counted.

- GLB: **470,632 bytes, 6,860 triangles**, 19 render primitives / 13 editable source modules. Budgets 800,000 bytes / 16,000 triangles. Original untextured geometry, five materials. Khronos zero errors/warnings. Precise glTF dimensions **1.650 × 2.048 × 0.932 m** (X/Y/Z); floor at Y≈0. See [assets](reports/assets.json).
- [Source inspection](reports/sources.json): reopened delivered .blend, metre units, unit scales, no external unpacked images, zero nonmanifold edges or degenerate faces across evaluated parts, positive volumes, readable outward text inside sign bounds.
- [Source edit](reports/source-edit.json): actual counter mesh widened 4%, jade material changed red and sign changed LOCAL GIFTS; saved/reopened/re-exported test copy. Delivered source hash unchanged.
- Four studio views and actual Gallery images inspected: recognizable cart proportions, canopy/posts/casters visible, rear shelf open, sign not mirrored or clipped. Studio [front](previews/front.webp), [rear](previews/rear.webp), [side](previews/side.webp).
- [Strict browser](reports/browser/results.json): **3/3**, desktop Chromium at 1440, 768 and 390 px. Exact consumed GLB bytes/SHA, HTTP200, real draw calls, orbit/zoom, exact reset, close/reopen, three same-page lifecycle repeats, focus restoration, stopped render loop, no horizontal overflow or filtered request/console/page errors. This is NOT physical Android/iOS coverage.
- First base unit run **165/165** and production build/all catalog GLB validation pass. Final **168/168** unit tests and production rebuild PASS after three asset-specific tests and metadata metrics were added; logs `reports/unit-final.log` and `reports/build-final.log`.

Historical setup/check errors preserved: initial Blender command lacked background mode and could not open X11 (`reports/generate.log`); corrected background invocation succeeded. Initial dimensions check used conservative transformed AABBs and overstated canopy bounds (`reports/validate-initial-failure.log`); precise per-vertex Three.js bounds match reopened Blender source. Geometry was not altered and dimension thresholds were not relaxed.

No main merge, push, PR or deployment performed for this preparation. No safety, engineering or commercial brand certification. Source editability and viewer orbit controls do not imply runtime cart interaction.

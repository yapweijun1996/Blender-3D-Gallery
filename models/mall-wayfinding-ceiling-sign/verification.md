# Verification · Mall Wayfinding Ceiling Sign · 438

Prepared locally on initial base 63a8da8f3bbb6195ca07e3350c3f6aa665ced4c6. This is second-batch item 9/10, not a final merged-base or release pass. No push, PR, merge or deployment performed.

## Asset and editable source

- Exact GLB SHA-256: dd0db4a794d01dfb25b6cc6f494e7285e9fe42de7a70673a596e848563dc0c14.
- 676,028 bytes; 11,524 triangles; 25,667 vertices; 18 primitives across 11 independent semantic modules; 4 materials; no textures, animations or external buffers.
- Khronos Validator 2.0.0-dev.3.10: **0 errors, 0 warnings**.
- Measured GLB dimensions: 2.10 m wide × 0.94 m drop × 0.162 m deep. Ceiling plane glTF Y=0, all geometry below. Exported mount anchors at (-0.70,0,0) and (0.70,0,0).
- Delivered Blender 4.0.2 source reopened. Metres, unit scales, ten editable FONT labels, all evaluated export geometry closed with positive volume and zero degenerate faces. Text fits its allocated columns/header bounds.
- Front is Blender -Y / glTF +Z. Rear is a proper 180-degree rotation with determinant +1, not negative scaling. Both faces read left-to-right. Opposite-view left/right arrows are reversed.
- Source export evaluation welds Blender FONT boundary duplicates and dissolves collinear cap diagonals before triangulation. This repaired a development topology finding; it does not modify the original editable FONT objects or weaken the topology assertions.
- Real saved-source proof: SHOPS changed to STORES and front FOOD arrow left changed to right; edited .blend saved, reopened and exported without regeneration. Only FrontText and FrontArrows changed. All nine other modules and all transforms remained identical; shipped source unchanged. Edited GLB also Khronos 0/0.
- Seven PNG masters and WebPs: hero, front, rear, rear-angle, side, mount, ceiling-context. The context ceiling is not exported.
- All studio images and all 36 strict-browser captures inspected. Readable labels/icons, proper rear lettering, no face-layout collision, no missing geometry or clipping. Browser viewer framing contains both suspension rods and plates. Mobile screenshot inspected at full viewport size.
- Parent independently inspected front, rear and 390-pixel initial view and accepted the visual result before local commit.
- Existing floor-direction sign source and metadata inspected: that asset is a 2.53 m freestanding totem with weighted base. This horizontal suspended double-sided sign is distinct.

## Local initial-base gates

- Focused contracts: **6/6 passed**.
- Full unit suite: **165/165 passed**.
- Production build and catalog asset validation: **passed**. Existing bundle-size warning remains.
- Library browser suite: **9/9 passed**.
- Strict viewer: exactly one fixed pass, desktop Chromium 156.0.8078.4 on shared Ubuntu with viewport emulation:
  - 1440 × 900: **FAIL**, one unfiltered GET GLB net::ERR_ABORTED.
  - 768 × 1024: **FAIL**, one unfiltered GET GLB net::ERR_ABORTED.
  - 390 × 844: **FAIL**, two unfiltered GET GLB net::ERR_ABORTED.
- All three verified exact consumed SHA and bytes, HTTP 200 GLB responses, rendering, orbit, zoom, pixel-exact reset/reopen, three repeated lifecycle cycles, stopped rendering on close, restored card focus, disabled download and no horizontal overflow.
- These existing-loader failures remain failures. No retries, error filtering, loader fix, app/UI/schema additions or unmerged first-batch implementation copy.

## Preservation and limits

Main was rechecked immediately before final gates: b7421d284b503ff923508fc3046b2193108f503a. PR 12 head remained 04d31c694520a0935a6c0e65b737bd91f43a8bc6. Final merged-base integration is still **PENDING**.

All previous tracked files and asset/evidence bytes, including prepared items 430–437, remain unchanged. The existing catalog schema, entry order, rights and metadata are preserved, with one collection appended and downloadable=false. Only the new asset, its tests and its evidence are added.

Physical Android/iOS hardware **NOT TESTED**. Static illustrative wayfinding prop only, with no live navigation, safety/egress, accessibility, structural or installation-compliance claim.

Evidence: reports/assets.json, geometry.json, sources.json, source-edit.json, preservation.json, unit-focused.log, unit-full.log, build.log, browser.log, browser/results.json, library.log and upstream-before-gates.txt. Browser evidence is for this exact optimized GLB, not the eventual merged base.

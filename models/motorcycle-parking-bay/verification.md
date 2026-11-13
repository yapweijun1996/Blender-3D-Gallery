# Motorcycle Parking Bay verification

V2.1 backlog **387**. **Local asset PASS; overall NEEDS REVIEW**: physical Android/iOS browsers/devices are **NOT TESTED**. Desktop viewport emulation is not native mobile acceptance. No remote push, PR, merge or deployment by this preparation.

## Asset and provenance

Open three-space motorcycle parking module with painted bay lines, wheel stops and a separate original two-wheel pictogram panel.

Three0.9m-spaced illustrative parking spaces with editable markings/stops and an original motorcycle pictogram. Overall width3.175m includes projecting sign, while slab is3.1m. See reports/initial-review.txt for the corrected mistaken width expectation, initial images and caught incomplete pictogram edit. Final engine/saddle meshes are asserted and visually inspected.

Independent original Blender Python geometry and materials, using reviewed original project helpers. No third-party models, textures, fonts or logo artwork. Original geometric symbols are illustrative, not an official road sign or regulatory/engineering/structural/accessibility certification. Reuse in the owner's projects authorized; public redistribution terms unspecified and downloads disabled.

- [Generator](generate.py), [editable source](sources/motorcycle-parking-bay.blend), [GLB](exports/motorcycle-parking-bay.glb), [metadata](metadata/motorcycle-parking-bay.json).
- Metres; Blender +Z up/-Y front exports to glTF +Y up/+Z front.
- Actual source reopen and independent mesh data: [report](reports/source.json).
- Actual component edit/re-export **PASS**, original source preserved: [proof](reports/source-edit-proof.json), [edited source](reports/source-edit.blend), [edited GLB](reports/source-edit.glb). Editable components are not runtime interaction claims.

## Executed checks

- [Structural report](reports/assets.json): **0 Khronos errors, 0 warnings**; 140,804 bytes, 2,592 triangles, 18 primitives, 5 materials.
- Budget **500 KiB / 12,000 triangles** passes. Validator asserts expected parts, finite geometry, scale/orientation and no external buffers/textures, animations, cameras or lights.
- **235/235 unit tests PASS**, including five new tests. Build/catalog validation **PASS**, existing chunk-size warning retained. Shared [unit log](../malaysia-card-lane-sign/reports/unit-full.log), [build log](../malaysia-card-lane-sign/reports/build.log).
- Strict desktop Chromium **3/3 PASS**, version 156.0.8078.4, at1440×900,768×1024,390×844. [Results](reports/browser/results.json), [log](reports/browser.log). Exact consumed GLB bytes/SHA, HTTP200, WebGL draws, orbit/zoom, exact reset/reopen, no overflow and no unfiltered request/page/console errors. One fixed browser pass, no error filtering or retry-to-green.

## Visual review and limits

Actual exported-GLB studio renders inspected: [primary](previews/motorcycle-parking-bay.webp), [front](previews/front.webp), [rear](previews/rear.webp). Actual Gallery initial pixels inspected at all three widths. Recognizable proportions, visible separate components/markings and no clipped framing. No per-model lighting adjustment needed. WebP thumbnails are lightweight; larger lossless PNG renders are retained as evidence, not claimed under the proposed300KiB poster budget.

Combined ten-model final gate is pending with assembler. Physical Android/iOS and device performance remain unverified. Existing models, catalog schema and historic evidence preserved.

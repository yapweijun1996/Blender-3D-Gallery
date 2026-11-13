# Malaysia Touch 'n Go Lane Sign verification

V2.1 backlog **385**. **Local asset PASS; overall NEEDS REVIEW**: physical Android/iOS browsers/devices are **NOT TESTED**. Desktop viewport emulation is not native mobile acceptance. No remote push, PR, merge or deployment by this preparation.

## Asset and provenance

Generic Malaysian electronic-payment lane sign with editable card pictogram and directional arrow; no proprietary logo or regulatory claim.

The backlog title names Touch 'n Go context, but the asset deliberately uses an original generic card-and-arrow pictogram, not that company's proprietary logo, trade dress or operational specification. Panel is independently editable.

Independent original Blender Python geometry and materials, using reviewed original project helpers. No third-party models, textures, fonts or logo artwork. Original geometric symbols are illustrative, not an official road sign or regulatory/engineering/structural/accessibility certification. Reuse in the owner's projects authorized; public redistribution terms unspecified and downloads disabled.

- [Generator](generate.py), [editable source](sources/malaysia-card-lane-sign.blend), [GLB](exports/malaysia-card-lane-sign.glb), [metadata](metadata/malaysia-card-lane-sign.json).
- Metres; Blender +Z up/-Y front exports to glTF +Y up/+Z front.
- Actual source reopen and independent mesh data: [report](reports/source.json).
- Actual component edit/re-export **PASS**, original source preserved: [proof](reports/source-edit-proof.json), [edited source](reports/source-edit.blend), [edited GLB](reports/source-edit.glb). Editable components are not runtime interaction claims.

## Executed checks

- [Structural report](reports/assets.json): **0 Khronos errors, 0 warnings**; 39,096 bytes, 625 triangles, 9 primitives, 4 materials.
- Budget **500 KiB / 12,000 triangles** passes. Validator asserts expected parts, finite geometry, scale/orientation and no external buffers/textures, animations, cameras or lights.
- **235/235 unit tests PASS**, including five new tests. Build/catalog validation **PASS**, existing chunk-size warning retained. Shared [unit log](../malaysia-card-lane-sign/reports/unit-full.log), [build log](../malaysia-card-lane-sign/reports/build.log).
- Strict desktop Chromium **3/3 PASS**, version 156.0.8078.4, at1440×900,768×1024,390×844. [Results](reports/browser/results.json), [log](reports/browser.log). Exact consumed GLB bytes/SHA, HTTP200, WebGL draws, orbit/zoom, exact reset/reopen, no overflow and no unfiltered request/page/console errors. One fixed browser pass, no error filtering or retry-to-green.

## Visual review and limits

Actual exported-GLB studio renders inspected: [primary](previews/malaysia-card-lane-sign.webp), [front](previews/front.webp), [rear](previews/rear.webp). Actual Gallery initial pixels inspected at all three widths. Recognizable proportions, visible separate components/markings and no clipped framing. No per-model lighting adjustment needed. WebP thumbnails are lightweight; larger lossless PNG renders are retained as evidence, not claimed under the proposed300KiB poster budget.

Combined ten-model final gate is pending with assembler. Physical Android/iOS and device performance remain unverified. Existing models, catalog schema and historic evidence preserved.

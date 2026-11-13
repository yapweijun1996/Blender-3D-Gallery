# Mamak Stainless Steel Plate verification

V2.1 backlog **377**. **Local asset PASS; overall NEEDS REVIEW**: physical Android/iOS browsers and devices are **NOT TESTED**. Viewport emulation is not native mobile acceptance. No remote push, PR, merge or deployment by this preparation.

## Asset and provenance

Shallow round stainless dining plate with a real recessed bowl, rolled rim and separate underside foot ring.

Original generic illustrative prop, not an official product or certified food-contact appliance. Independent Blender Python geometry and Principled materials using reviewed project helpers. No third-party model, font, texture, brand or logo. Reuse in the owner's projects authorized; public redistribution terms unspecified and downloads disabled. No runtime cooking, pouring or interaction simulation.

- [Generator](generate.py), [editable source](sources/mamak-stainless-steel-plate.blend), [GLB](exports/mamak-stainless-steel-plate.glb), [metadata](metadata/mamak-stainless-steel-plate.json).
- Metres; Blender +Z up/-Y front exports to glTF +Y up/+Z front.
- Actual source reopen and independent mesh data: [report](reports/source.json).
- Actual source edit/re-export **PASS**, original source preserved: [proof](reports/source-edit-proof.json), [edited source](reports/source-edit.blend), [edited GLB](reports/source-edit.glb). Editable components are not runtime interaction claims.

## Executed checks

- [Structural report](reports/assets.json): **0 Khronos errors, 0 warnings**; 100,036 bytes, 2,428 triangles, 3 primitives, 1 materials.
- Budget **150 KiB / 5,000 triangles** passes. Validator asserts expected parts, finite geometry, scale/orientation and no external buffers/textures, animations, cameras or lights.
- **235/235 unit tests PASS**, including five new tests. Build/catalog validation **PASS**, existing chunk-size warning retained. Shared [unit log](../mamak-teh-tarik-jug/reports/unit-full.log), [build log](../mamak-teh-tarik-jug/reports/build.log).
- Strict desktop Chromium **3/3 PASS**, version 156.0.8078.4, at 1440×900, 768×1024, 390×844. [Results](reports/browser-final/results.json), [log](reports/browser-final.log). Exact consumed GLB bytes/SHA, HTTP200, WebGL draws, orbit/zoom, exact reset/reopen, no overflow and no unfiltered request/page/console errors. No error filtering or retry-to-green.

## Visual inspection and limitations

Actual exported-GLB studio renders inspected: [primary](previews/mamak-stainless-steel-plate.webp), [front](previews/front.webp), [third](previews/rear.webp). Actual Gallery initial pixels inspected at all three widths. Recognizable proportions, visible independent parts and no clipped framing. Metal reflects differently in studio and Gallery; raised-lid cavity has some sampling grain, not claimed photorealistic.

Initial strict 3/3 passed but visual inspection found the plate too dark. Original browser evidence remains under reports/browser and initial-visual-review.txt. Only the already-supported per-model directional light position changed to [-4,3,-5], aligning the key reflection with the shallow metal surface. Source, GLB and materials are unchanged. Build and full 235 tests passed again; affected final 3/3 passed. Final actual pixels at all widths were inspected: bright steel surface, recessed bowl and rolled rim are visible, without clipping. This is not a claim that the initial dark preview passed visual review.

Combined ten-model final gate is pending with assembler. Physical Android/iOS and device performance remain unverified. Existing models, catalog schema and historic evidence preserved.

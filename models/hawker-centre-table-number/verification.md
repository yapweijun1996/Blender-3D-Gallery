# Hawker Centre Table Number verification

V2.1 backlog **367**. **Local asset PASS; overall NEEDS REVIEW** because physical Android/iOS browsers and devices are **NOT TESTED**. Desktop viewport emulation is not native mobile acceptance. No push, PR, merge or deployment by this preparation.

## Asset and provenance

0.14 m wide freestanding, double-sided A-frame table tent. Both faces show original geometric 12 digits. This is a different physical form/use from the wall plaque, not an extra counted number or color variant.

Original generic hawker/kopitiam visual prop, not an official product, certified appliance or food-contact item. Independent Blender Python geometry and Principled materials; reviewed original project helpers. No external model, texture, font or brand artwork. Contextual reuse is credited above and in metadata. Reuse in the owner's projects authorized; public redistribution terms unspecified and downloads disabled.

- [Generator](generate.py), [editable source](sources/hawker-centre-table-number.blend), [GLB](exports/hawker-centre-table-number.glb), [metadata](metadata/hawker-centre-table-number.json).
- Metres; Blender +Z up/-Y front exports to glTF +Y up/+Z front.
- Actual source reopen and independent mesh-data inspection: [source report](reports/source.json).
- Actual source edit/re-export proof **PASS**, original source preserved: [proof](reports/source-edit-proof.json), [edited GLB](reports/source-edit.glb), [edited source](reports/source-edit.blend). Editable poses are not runtime interactions.

## Executed checks

- [Structural report](reports/assets.json): **0 Khronos errors, 0 warnings**; 100,512 bytes, 1,836 triangles, 17 mesh primitives, 2 materials.
- Budget **100 KiB / 3,000 triangles** passes. [Validator](validate.mjs) asserts known parts, scale/datum, finite geometry and no external textures/buffers, animations, cameras or lights.
- **235/235 full unit tests PASS**, including five new structural tests. Production build/catalog validation **PASS**, retaining existing chunk-size warning. Shared [unit log](../hawker-stall-number-plate/reports/unit-full.log), [build log](../hawker-stall-number-plate/reports/build.log).
- Strict desktop Chromium **3/3 PASS**, version **156.0.8078.4**, at1440×900,768×1024,390×844. [Results](reports/browser/results.json), [log](reports/browser.log). Exact consumed bytes/SHA, HTTP200, WebGL draws, orbit/zoom, exact reset/reopen, no horizontal overflow or unfiltered request/console/page errors. No retry-to-green or error filtering.

## Visual review and limits

Three actual exported-GLB studio views were inspected: [primary](previews/hawker-centre-table-number.webp), [front](previews/front.webp), [rear](previews/rear.webp). Actual Gallery initial pixels were inspected at all three widths. Shapes/digits are recognizable and fit without clipping; materials and separate components are visible. Metallic parts are naturally darker under the Gallery's lighting than under studio lights.

Physical Android/iOS, device performance and runtime operation remain unverified. Combined final10-model gate is pending with the batch assembler. Existing models/catalog schema/test evidence preserved.

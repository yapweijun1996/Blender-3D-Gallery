# HDB Bin Centre verification

V2.1 backlog **315**. **Local asset PASS; overall NEEDS REVIEW.** Physical Android/iOS browsers/devices are **NOT TESTED**. Desktop viewport emulation is not native mobile acceptance. No push, PR, merge or deployment is performed by this preparation.

## Scope and provenance

5.00 × 3.40 m roof footprint, 2.88 m overall height. Separate enclosure, two hinged louvered leaves, 24 louvers and two contextual wheeled bins. Included bins are assembly context, not counted as additional new assets.

Original generic HDB-inspired visual module, not a surveyed estate, official HDB design, structural/fire/accessibility certification or construction detail. Geometry and materials use original Blender Python and reviewed original project helpers. No third-party models, textures, fonts, brands or artwork. Original geometric symbols are built from primitives. Reuse in the owner's projects is authorized; public redistribution terms unspecified, downloads disabled.

- [Generator](generate.py), [editable Blender source](sources/hdb-bin-centre.blend), [GLB](exports/hdb-bin-centre.glb), [metadata](metadata/hdb-bin-centre.json).
- Metres; Blender +Z up/-Y front → glTF +Y up/+Z front; base grounded at Y=0.
- Actual source reopen verified independent mesh data and finite geometry: [source report](reports/source.json).
- Actual source edit/re-export passed while original source remained unchanged: [proof](reports/source-edit-proof.json), [edited GLB](reports/source-edit.glb), [edited blend](reports/source-edit.blend). This is editable geometry, not runtime interaction.

## Executed quality gate

- [GLB validation](reports/assets.json): **0 Khronos errors, 0 warnings**; 283,812 bytes, 5,208 triangles, 50 mesh primitives, 5 materials.
- Budget **1 MiB / 20,000 triangles** passes. Named parts, scene units, grounding, key dimensions and finite geometry asserted in [validator](validate.mjs). No external buffers/textures, animations, cameras or lights.
- **228/228 full unit tests PASS**, including five new asset structural tests; production build/catalog validation **PASS**. Shared [unit log](../hdb-bin-centre/reports/unit-full.log), [build log](../hdb-bin-centre/reports/build.log). Existing chunk-size warning retained.
- Strict desktop Chromium **3/3 PASS**, version **156.0.8078.4**, at 1440×900, 768×1024 and 390×844. [Results](reports/browser/results.json), [log](reports/browser.log). Exact consumed bytes/SHA, HTTP200, draws, orbit/zoom, exact reset/reopen, no horizontal overflow or unfiltered request/console/page errors. No retries-to-green.

## Visual inspection and chronology

Three multi-angle studio previews rendered from actual shipped GLB and inspected: [primary](previews/hdb-bin-centre.webp), [front](previews/front.webp), [rear](previews/rear.webp). Actual Gallery initial pixels inspected at all three widths: recognizable form, visible parts and unclipped fit.

Initial front studio views showed the orthographic camera near plane intersecting the large ground plane; moving front cameras backwards along the same look vector removed the cut-off. Hall studio lights were also distributed to fit its larger footprint rather than concentrating a highlight on the roof. Final front views and updated hall three-quarter/rear views were reinspected. [Initial and intermediate previews](reports/initial-studio/) and original/final render logs are preserved.

GLBs, materials and viewer behavior did not change during final front-only studio refinement. Strict browser checks preceded that final front-only image update; production build was rerun afterward. Final combined 10-model gate remains the batch assembler's next step.

## Limitations

No physical Android/iOS or device-performance result; no runtime simulation, complete-building engineering or release claim. Existing models, tests and catalog schema preserved.

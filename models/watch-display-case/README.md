# Watch Display Case

Original brand-neutral procedural showcase for GJH Virtual Mall, store **S15**, priority **P2**, existing category **Retail**. Status: draft / **NEEDS REVIEW**, pending manager art approval.

The counter has a pale panelled base, recessed dark plinth, champagne frame, five transparent glass panels, a deep teal velvet-look tray and eight individual cushions. Four round and four square wrist watches have geometric hands, baton markers, crowns, lugs and looped straps; three straps use alternating metal-link colours. Two warm edge lighting strips share the hardware material through an original **4 × 2 PNG emission mask**. No readable text, brands, external assets or real packaging.

Measured export: **1 × 0.96 × 0.5 m** (width, height, depth), **14,260 triangles**, **16,631 vertices** and **763,804 bytes**. The source retains **231 editable mesh parts** and eight watch groups. The GLB batches these into **three meshes / three primitives / three shared materials**. The velvet look uses a rough matte finish; lightweight alpha-blended glass avoids a transmission render pass. The emission mask is embedded in the GLB and packed in the source. Studio floor, lights and camera are excluded from export.

Units are metres. Blender uses +Z up / -Y front; glTF uses +Y up / +Z front. The origin is at the floor centre of the full base footprint. Measured bounds, geometry counts and tested SHA-256 are in `reports/assets.json` and metadata. No random inputs are used. The independent clean-directory rebuild checks exact GLB byte reproducibility with Blender 5.2.3.

From the repository root:

```sh
/opt/homebrew/bin/blender --background --python models/watch-display-case/generate.py
node models/watch-display-case/validate.mjs
/opt/homebrew/bin/blender --background --python models/watch-display-case/inspect_sources.py
node models/watch-display-case/verify_source_edit.mjs
npm run validate:assets
npm test
npm run build
node models/watch-display-case/verify_page.mjs
```

Append `-- --export-source --skip-render` to export saved source edits without regenerating the geometry. Export bakes evaluated parts into temporary material batches and preserves the editable source. Per-primitive triangle indices are sorted after export to remove exporter thread-dependent ordering; vertex attributes and winding remain intact. Source inspection reopens the file, checks closed solids, counts watch features, measures merchandise clearance, and edits a disposable source copy before independently checking its GLB. Reproducible scratch exports are ignored under `reports/source-edit/`.

The folder layout, generation/export path and layered quality gate follow `../self-checkout-machine/`; shared-material batching and browser verification follow the existing battery rack pattern. `reports/duplicate-search.json` records the catalog and recursive metadata search. The nearest existing model is a 1.8 m upright shelved glass tower with no watch tray or merchandise; no close match was found.

`reports/acceptance.json` records final checks and their scope. Actual hero/front/side/3q renders and a 1440 × 900 Chromium model-page screenshot are reviewed visually. Initial validation and appearance failures are retained in the reports; a previous test launch before the thumbnail existed was a sequencing error and is recorded separately from the final gates.

Static visual prop only. Watch operation, cabinet opening, safety glazing, load/stability certification, physical Android/iOS, WebKit and full 17-shop 70 × 60 m mall integration/performance are unverified. Three asset primitives do not establish the complete mall's 200 draw-call budget. Public redistribution terms remain unspecified. No push or deployment.

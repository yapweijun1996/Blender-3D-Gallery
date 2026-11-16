# Pharmacy Counter

Original, brand-neutral pharmacy service station for GJH Virtual Mall stores S04/S05/S12, priority P2. Existing category: **Equipment**. Status: draft / **NEEDS REVIEW** pending manager art review. No external geometry, images, textures, fonts, medication packaging, logos, cross symbols or brand text.

The complete station occupies 3.000 × 0.800 m and stands 2.220 m high. The service top is 0.900 m above the floor. Three transparent glass panes surround a real central aperture measuring 0.814 m wide and 0.304 m above the worktop (0.264 m clear above the tray lips). The empty pickup tray bridges that aperture. A shallow, open, two-column dispensing rack stands on the rear left edge, with four shelf boards forming three storage tiers; staff access is from the rear. A small customer-facing display shows static mesh numerals `042`. The overhead panel is blank on both sides. The staff working aisle is outside the asset footprint.

Measured export: 6,696 triangles, 9,062 vertices, 260,664 bytes, three meshes/primitives and three shared materials, no images or clips. Warm porcelain cabinetry, graphite worktop/frame and lightly tinted transparent glazing. The native source retains 62 named editable mesh parts; export evaluates their saved modifiers and batches copies by material without changing the source. Studio floor, camera and lights are excluded from the GLB.

Metres; origin at the floor centre of the complete footprint. Blender +Z up / -Y front; exported glTF +Y up / +Z front.

From the repository root:

```sh
/opt/homebrew/bin/blender --background --python models/pharmacy-counter/generate.py
node models/pharmacy-counter/validate.mjs
/opt/homebrew/bin/blender --background --python models/pharmacy-counter/inspect_sources.py
node models/pharmacy-counter/verify_source_edit.mjs
npm run validate:assets
npm test
npm run build
node models/pharmacy-counter/verify_page.mjs
```

Generator options after `--`: `--skip-render`, `--views=hero,front,side,3q,rear`, or `--export-source` to export the saved `.blend` without rebuilding. Rebuilding overwrites this asset's source/export/previews. Source inspection creates ignored disposable edit copies in `reports/source-edit/`.

Duplicate review searched every catalog asset and metadata file: [comparison evidence](reports/duplicate-search.json). `clinic-pharmacy-window` is an independent architectural sliding window and ledge, `medicine-cabinet` is a hinged storage case, and `bank-teller-counter` is a transaction desk without the dispensing rack, queue screen or blank overhead sign. This station uses original geometry and preserves those models. Existing catalog entries and gallery UI are unchanged.

Evidence: [GLB measurements](reports/assets.json), [Khronos](reports/khronos.json), [saved-source inspection](reports/sources.json), [deterministic rebuild](reports/reproducibility.json), [catalog preservation](reports/catalog-preservation.json), [acceptance](reports/acceptance.json).

Static visual asset: no operational queue, dispensing logic, moving glazing or medical function. Three primitives do not establish the complete mall's 200 draw-call budget. Physical devices, WebKit, full 17-shop assembly, staff-aisle clearances, hygiene, structural and regulatory compliance are unverified. No push, publication or release is included.

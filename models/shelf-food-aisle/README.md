# Food Aisle Gondola Shelf

Original brand-neutral, static food-aisle fixture for the GJH Virtual Mall.
Category: existing **Mall Fixtures**. Status: **draft / needs owner review**.

Measured GLB: **1.20000005 x 0.5 x 1.80000007 m** (width, depth, height),
**16,320 triangles**, **1,022,748 bytes**, three meshes/primitives and three shared
materials. Metres, floor-centred origin; Blender +Z up / -Y front exports to glTF
+Y up / +Z front. There are five levels on each face, ten blank price rails,
two blank end signs, 30 cartons, 20 cans and 20 sealed pillow bags. Vertex colours
provide plain muted colours without textures, labels, logos or text.

The layout, editable source, source-export mode and quality gate follow
`models/self-checkout-machine`. Components stay separate in the `.blend`;
exporting batches them by material to reduce the runtime cost to three draws.
No third-party assets are used. The stock is illustrative; this asset provides
no stocking or purchase interaction.

Run from the repository root:

```sh
/opt/homebrew/bin/blender --background --python models/shelf-food-aisle/generate.py
/opt/homebrew/bin/blender --background --python models/shelf-food-aisle/inspect_sources.py
/opt/homebrew/bin/blender --background --python models/shelf-food-aisle/verify_reproducibility.py
node models/shelf-food-aisle/validate.mjs --update-metadata
npm run validate:assets
npm test
npm run build
node models/shelf-food-aisle/check_page.mjs
git checkout -- models/demo-beverage-can/reports/structure-motion.json
```

Use Blender **5.2.3 LTS**. `generate.py` rebuilds the source; append
`-- --export-source --skip-render` to export saved edits without rebuilding.
`-- --skip-render` skips preview renders. `inspect_sources.py` inspects the saved
source, checks closed components and stock clearance, and saves/exports a
controlled edit in the OS temporary directory without changing delivery files.
The Node gate independently loads that edit. The reproducibility check compares
the delivered GLB, saved-source export and clean procedural rebuild by SHA-256.

Duplicate search covered 607 existing catalog assets and 650 metadata files.
The closest `supermarket-aisle` has four levels, a long aisle footprint and only
cartons. `mall-display-shelf`, the premium wall shelf family and
`medicine-health-box-set` also differ in layout, function or stock. Full evidence
is in `reports/duplicate-search.json`; no exact equivalent was found.

Previews `hero.png`, `front.png`, `side.png` and `3q.png` were visually inspected.
The production page screenshot is saved under
`~/Documents/MallQueue/reports/shelf-food-aisle-page.png`. Reports record the tested
GLB hash and coverage. Physical devices, WebKit, structural loading, complete
17-shop integration and sustained mall performance remain unverified. No push or
deployment is part of this delivery. Public redistribution terms are unspecified.

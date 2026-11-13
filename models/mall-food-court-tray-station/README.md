# Mall Food Court Tray Station

Exact V2.1 P0 **439**. Second-batch item **10/10**, prepared locally on the inherited current base. Final merged-base integration remains **PENDING**; this is not a release.

A generic Singapore/Malaysia mall food-court tray return station, distinct from the separate waste-sorting station and coffee counters. Teal cabinet sides and back, two open stainless shelves, stainless counter, an original **TRAY RETURN / Thank you** sign and four independent hollow terracotta trays. The included trays do not add backlog model types.

## Editable modules and metric layout

- Floor-centred origin, Blender -Y front / +Z up, glTF +Z front / +Y up; metres with unit scale.
- Overall **1.50 W × 0.66 D × 1.49 H m**. Countertop height **0.95 m**.
- Thirteen independent export modules: left/right/back cabinet panels, two shelves, counter, feet, sign frame, sign lettering, and four trays. Original source keeps every panel/foot and both FONT labels independently editable, with named materials.
- **1.36 m** clear shelf opening width, **0.33 m** vertical clearance in each bay. No false black aperture or solid hidden blocking box.
- Each tray is **0.45 × 0.33 × 0.03 m**, with a real recessed 6 mm floor, sloped bowl and lip. Three trays form a small lower stack; the fourth sits independently on the upper shelf.
- Live exported-geometry checks verify hollow tray floors, 3 mm shelf-to-tray clearance, 5 mm stack gaps, and a collision-free **0.62 m** forward removal sweep that completely clears the cabinet/counter footprint.
- `tray-removal.png` is a geometric Blender-source demonstration only. The delivered GLB remains the closed static arrangement; there is no runtime tray control or automation.

## Files and reproduction

- `generate.py`: self-contained deterministic source and GLB generator.
- `sources/mall-food-court-tray-station.blend`: editable Blender 4.0.2 source, no external assets.
- `exports/optimized.glb`: semantic module joins, baked bevels, no textures or animation.
- `previews/`: six 768 px PNG masters and lightweight WebPs. Hero, front, rear, side, interior detail and tray-removal pose. The interior view intentionally crops the header to inspect shelves.
- `metadata/`, `reports/`, `verification.md`: measured metrics, provenance, validation and explicit limits.

From the repository root, with Blender 4.0.2, Node dependencies and Pillow available:

```sh
blender --background --threads 2 --python-exit-code 1 --python models/mall-food-court-tray-station/generate.py
blender --background --threads 2 --python-exit-code 1 --python models/mall-food-court-tray-station/generate.py -- --export-source
blender --background --threads 2 --python-exit-code 1 --python models/mall-food-court-tray-station/inspect_sources.py
node models/mall-food-court-tray-station/verify_source_edit.mjs
blender --background --threads 2 --python-exit-code 1 --python models/mall-food-court-tray-station/render_views.py
python3 models/mall-food-court-tray-station/prepare_previews.py
node --test tests/mall-food-court-tray-station.test.mjs
npm test
npm run build
MALL_QA_DIR=/tmp/tray-station-439-qa node scripts/test-mall-food-court-tray-station.mjs
TEST_ARTIFACT_DIR=/tmp/tray-station-439-library node scripts/test-library-browser.mjs
```

The source-edit test uses a temporary saved copy: changes counter mesh vertices, one tray material and the editable sign text, saves/reopens that copy, and re-exports without regeneration. Shipped source bytes must remain unchanged. A tiny original FONT outline offset avoids a touching Bfont A contour; the initial topology failure is retained, not hidden.

## Rights and limitations

Original geometry and wording; no brand, third-party asset, downloaded font or external texture. Editable lettering uses bundled Blender Bfont. Owner-project reuse is authorized; public redistribution terms remain unspecified and downloads stay disabled. See `LICENSE.md`.

Illustrative static asset only, not a hygiene, safety, accessibility, structural or fabrication certification. It does not sort waste, wash trays or implement automation. Physical Android/iOS hardware **NOT TESTED**. Existing initial-base loader errors must remain reported. No app/UI/schema changes, push, PR, merge or deployment are part of this prepared-asset step.

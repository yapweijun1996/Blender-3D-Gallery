# Mall Lift Floor Indicator · V2.1 P0 432

One horizontal wall-mounted display: satin stainless bezel, thin charcoal cup housing, dark face, fourteen separately editable seven-segment digit meshes and three arrow meshes. The example shows **02 and an up arrow**. No buttons, call panel 431 or complete lift is included.

## Artifacts and measurements

- `sources/mall-lift-floor-indicator.blend`, deterministic `generate.py`, self-contained `exports/optimized.glb`.
- 43,292-byte GLB; 596 triangles; 1,104 vertices; 20 named mesh primitives; five materials; zero textures or animations. Khronos: zero errors and warnings.
- Five 768 × 768 PNG masters and lightweight WebPs: hero, front, side, rear, digit detail. Studio wall, lights and camera are excluded from export.
- Metadata, interface, provenance, rights and measured asset/source-edit reports.

## Placement and source editing

Units are **metres**. Blender +Z is up and -Y is front; glTF +Y is up and +Z is front. Overall width × height × depth: **420 × 160 × 26.8 mm**. Root sits at bottom centre on the wall plane. `CONNECTOR_WallMount` is Blender (0, 0, 0.08), glTF (0, 0.08, 0). The consuming scene chooses mounting height. Housing back and sides are 1.5 mm; bezel is 3 mm deep. These are visual dimensions, not fabrication or mounting certification.

All meshes can be edited without rebuilding other components. On root `ASSET_MallLiftFloorIndicator`, edit `display_floor` to any two decimal digits and `display_direction` to `up` or `down`. Apply with `apply_display(root)` from the generator, or export using the source-preserving path. Export updates only the digit segment materials and direction-group pose. It does not rebuild housing, face or segment geometry.

```sh
# Preserve edits in the saved source; do not use the default rebuilding mode.
blender --background --threads 2 --python-exit-code 1 --python models/mall-lift-floor-indicator/generate.py -- --export-source --skip-render
```

Actual proof reopens the delivered `.blend`, changes **02/up to 03/down**, applies configuration, saves an isolated copy, reopens it and exports. The GLB changes only digit-1 segment c/e illumination and the arrow pose. All 20 mesh coordinate arrays, housing placement and the delivered source bytes remain unchanged.

## Reproduction and checks

Blender 4.0.2 and Python standard library; Pillow for WebP; existing Node repository dependencies for validation. No downloads, third-party artwork, fonts or textures.

```sh
blender --background --threads 2 --python-exit-code 1 --python models/mall-lift-floor-indicator/generate.py -- --skip-render
blender --background --threads 2 --python-exit-code 1 --python models/mall-lift-floor-indicator/render_views.py
python3 models/mall-lift-floor-indicator/prepare_previews.py
node models/mall-lift-floor-indicator/validate.mjs
blender --background --threads 2 --python-exit-code 1 --python models/mall-lift-floor-indicator/inspect_sources.py
node models/mall-lift-floor-indicator/verify_source_edit.mjs
node --test tests/mall-lift-floor-indicator.test.mjs
npm test
npm run build
node scripts/test-mall-lift-floor-indicator.mjs
npm run test:library
```

## Limits and rights

This is a **static visual display**, not live elevator state, runtime digit updates, electrical design, safety signage or code-compliant equipment. Emission is appearance only. Android/iOS hardware is **NOT TESTED**. Final merged-base integration is **PENDING**; see `verification.md` for the initial-base gates and retained browser failure.

Original asset; reuse in the owner's projects is authorized. Public redistribution terms have not been specified. Public download remains disabled. No merge, push, PR or deployment was performed for this prepared item.

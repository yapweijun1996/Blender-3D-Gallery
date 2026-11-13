# Mall Lift Call Panel · V2.1 P0 431

One wall-mounted lift call panel: satin metal faceplate, two separate circular buttons, up/down arrow geometry, polished bezels, four small fasteners and a thin charcoal cup housing. This is not a complete lift or item 432 floor indicator.

## Delivered files and measurements

- Editable `sources/mall-lift-call-panel.blend`, deterministic `generate.py` and self-contained `exports/optimized.glb`.
- GLB: 99,924 bytes; 2,608 triangles; 3,308 vertices; 16 named mesh primitives; six materials; zero textures and animations. Khronos: zero errors and warnings.
- Five faithful 768 × 768 source-rendered PNG/WebP views: hero, front, side, rear, button detail. Studio wall, camera and lights are not exported.
- Local metadata, interface, provenance, rights and measured validation/source-edit reports.

## Interface and editable parts

Units are metres. Blender +Z is up and -Y faces the user; glTF +Y is up and +Z faces the user. Root is at the bottom centre of the panel on the wall plane, Blender Y=0. `CONNECTOR_WallMount` is at Blender (0, 0, 0.17), so set installation height by placing that anchor in the consuming scene. No installation height, fastener specification or certified wall interface is prescribed.

Overall width/height/depth is 140 × 340 × 34.4 mm. The faceplate is 3 mm thick, with true circular apertures. Housing is a single connected cup with 1.5 mm walls and back. Faceplate, housing, both bezels, button caps, arrows and fasteners are independently editable meshes. No negative or non-unit scales are needed.

`PIVOT_Button_Up` and `PIVOT_Button_Down` independently parent the cap and its arrow. Rest centres in Blender are (0, -0.03225, 0.225) and (0, -0.03225, 0.115). Press by translating the selected pivot **+0.002 m on Blender Y** (glTF -Z), then restore it. Cap radius 24 mm versus aperture radius 25 mm gives 1 mm radial clearance. The 2 mm pressed pose clears the housing and keeps the cap face in front of the plate. These are modeled visual clearances, not validated operational dimensions.

Source inspection reopens the shipped `.blend`, poses each button without moving the other, makes a real isolated Up cap mesh edit (+2% X width) and presses only its pivot. It saves/reopens the edited copy and re-exports GLB, checking all 15 other mesh coordinate arrays remain unchanged. The delivered source remains unmodified.

## Scope and rights

Amber arrow emission is **static**. No runtime button interaction, elevator call, electrical connection, tactile/braille/code compliance, load or fabrication suitability is claimed. Wall material in studio previews is presentation-only. Android and iOS hardware are **NOT TESTED**. Final merged-base application integration remains pending; see `verification.md` for the initial-base results rather than treating source rendering as a browser pass.

Original asset; reuse in the owner's projects is authorized. Public redistribution terms have not been specified. `downloadable: false` is preserved.

## Reproduction

Blender 4.0.2, Python standard library; Pillow for WebP; repository Node dependencies for validation. No downloaded content or generation-time installation.

```sh
blender --background --threads 2 --python-exit-code 1 --python models/mall-lift-call-panel/generate.py -- --skip-render
blender --background --threads 2 --python-exit-code 1 --python models/mall-lift-call-panel/render_views.py
python3 models/mall-lift-call-panel/prepare_previews.py
node models/mall-lift-call-panel/validate.mjs
blender --background --threads 2 --python-exit-code 1 --python models/mall-lift-call-panel/inspect_sources.py
node models/mall-lift-call-panel/verify_source_edit.mjs
node --test tests/mall-lift-call-panel.test.mjs
npm test && npm run build
node scripts/test-mall-lift-call-panel.mjs
npm run test:library
```

To preserve an edited source, use `generate.py -- --export-source --skip-render`, not its default rebuilding mode.

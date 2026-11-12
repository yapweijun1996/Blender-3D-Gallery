# Mall Ceiling Panel Module

Selected backlog V2.1, item 422, P0. **One logical ceiling kit**, not a separate model per panel or hanger. Lights remain separate backlog item 423 and are not supplied here.

A 1.2 m × 1.2 m suspended ceiling cassette for generic Singapore/Malaysia mall interiors: four recessed mineral-fibre-style panels, an ivory T-grid and steel suspension pieces. Source uses metres with Blender +Z up; the GLB uses metres with +Y up. The origin is the centre of the visible grid underside. Hangers extend 0.36 m above it.

**Overall: NEEDS REVIEW.** See [verification.md](verification.md). The existing gallery camera starts above every ordinary asset, so this correctly upright ceiling initially shows its rear. The supplied thumbnail/multi-angle renders show the underside; use the gallery's existing down-arrow orbit control eight times to inspect it. No viewer code, UI or metadata-schema extension was made. Physical Android/iOS validation remains untested.

## Editable components and repeat rules

- Four separate 576 × 576 × 16 mm panels on a 600 mm pitch, with an 8 mm underside recess relative to the visible grid.
- Nine closed T-section rails. Internal visible flange width is 24 mm; each outer boundary contributes a 12 mm half-grid flange.
- Four hanger rods, four lower cleats and four top plates, each independently editable.
- Four named connector empties at the boundary midpoints. These are repeat-registration aids, not fabricated or certified structural fittings.
- Place **whole roots** at 1.2 m multiples in glTF X/Z at the chosen ceiling underside height Y. Quarter-turn Y rotations are supported. Blender equivalents are X/Y placement and Z rotation.
- Do not add duplicate boundary flanges or scale one module independently. The actual-export assembly test verifies 3 × 3 straight and alternating-quarter-turn arrangements, 60 panel gaps and 12 matching connector seams per layout.

The four named materials are editable. The original deterministic 256 × 256 mineral-fibre texture is packed in the source and embedded in the GLB; seed 422. No external artwork, font, model or network dependency is used. The asset export has no camera, light, animation or decoder dependency. Studio lights/camera in the source are excluded from the selected-root export.

This is a generic decorative concept, **not** an acoustic, fire, electrical, structural, load-bearing, installation or building-code specification.

## Reproduce

Blender 4.0.2, Python with Pillow, Node 22 and locked project dependencies:

```sh
python3 models/mall-ceiling-panel/make_texture.py
blender --background --threads 2 --python-exit-code 1 --python models/mall-ceiling-panel/generate.py -- --skip-render
blender --background --threads 2 --python-exit-code 1 --python models/mall-ceiling-panel/render_views.py
python3 models/mall-ceiling-panel/prepare_previews.py
blender --background --python-exit-code 1 --python models/mall-ceiling-panel/inspect_sources.py
node models/mall-ceiling-panel/validate.mjs
npm test
npm run build
node scripts/test-mall-ceiling-panel.mjs
npm run test:library
```

To keep manual source edits, run the generator with `--export-source --skip-render`. Without `--export-source`, it rebuilds and replaces the source. Back up manual edits first. Deterministic geometry does not imply identical binary bytes across Blender versions.

For the source-edit test, supply a fresh isolated absolute directory to `inspect_sources.py -- /fresh/directory`. It reopens the shipped source, lowers only the first panel's underside vertices by 2 mm, changes shared finish roughness from 0.85 to 0.65 and saves a separate source. Run the copied generator there with `--export-source --skip-render`, then `verify_source_edit.mjs /fresh/directory`. The check verifies all other geometry bounds, source hash and embedded texture remain unchanged.

The Node structural loader only inspects PNG dimensions; it does not pretend to decode rendered pixels. Pillow decodes the actual images, Blender renders the actual exported GLB, and Chromium renders the actual measured GLB bytes.

## Rights

Original geometry, materials and procedural texture authored for Blender-3D-Gallery. Reuse in the owner's projects is authorized. Public redistribution terms have not been specified. Public downloads remain disabled. No release, remote push, PR or deployment is asserted.

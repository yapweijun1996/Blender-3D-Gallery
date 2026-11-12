# Mall Ceiling Light Module

Selected backlog V2.1, P0 item 423. **One logical asset**, batch item 4/10. A simple original recessed square ceiling luminaire for generic Singapore/Malaysia mall scenes.

0.576 × 0.576 m footprint; 0.065 m overall height including rear driver cover and 1 mm projecting fastener heads. Blender metres +Z up; GLB metres +Y up. Origin is the centre of the bezel underside. The diffuser faces down, never inverted to fake the gallery's starting view.

## Editable parts and appearance

11 independently editable closed meshes: bezel, annular housing walls, diffuser, rear plate, driver cover, four visible fasteners and two rear cable-entry glands. Four named editable materials. No external textures, fonts or artwork; no decoder dependency. Studio camera/lights are excluded from export.

The opal diffuser has a **static emissive PBR material**, not a functional switch, punctual light or photometric model. It stays visible in a dark view but **does not illuminate neighbouring geometry in the Three.js gallery**. No electrical, fire, acoustic, structural, installation, lighting-performance or building-code compliance is claimed.

**Overall: NEEDS REVIEW.** Current gallery camera starts above the correctly oriented light, showing its rear. Eight down-arrow orbit steps expose the diffuser, with the existing upper-biased lighting still affecting the surrounding frame. A separate approved viewer-configuration task is not part of this asset commit. Physical Android/iOS remains untested.

## Mount into ceiling kit 422

1. Retain the entire ASSET_MallCeilingPanel root, grid, hangers and connectors.
2. Remove **only one** PANEL_1..4 child. Do not remove the kit root or leave that opaque panel behind the light.
3. Place ASSET_MallCeilingLight at the removed panel's horizontal centre. Blender X/Y are ±0.3 m; Z is ceiling root Z+0.008 m. In glTF, X/Z are the bay centre and Y is ceiling root Y+0.008 m.
4. Quarter-turn rotations are supported. Do not scale the light independently.
5. The other three panels, all nine grid rails and twelve suspension meshes remain untouched.

The actual-GLB assembly test checks all four bays in both default and quarter-turn orientations: identical retained transforms, no fixture AABB intrusion into retained geometry, matching footprint and visible diffuser surface rays. This documents scene assembly, not a fabricated support or certified installation.

## Reproduce

Blender 4.0.2, Python/Pillow, Node 22 and locked project dependencies:

```sh
blender --background --threads 2 --python-exit-code 1 --python models/mall-ceiling-light/generate.py -- --skip-render
blender --background --threads 2 --python-exit-code 1 --python models/mall-ceiling-light/render_views.py
python3 models/mall-ceiling-light/prepare_previews.py
blender --background --python-exit-code 1 --python models/mall-ceiling-light/inspect_sources.py
node models/mall-ceiling-light/validate.mjs
npm test
npm run build
node scripts/test-mall-ceiling-light.mjs
npm run test:library
```

To preserve manual source changes, add `--export-source --skip-render` to the generator. Normal generation rebuilds and replaces the source; back up manual edits first. Binary identity is not guaranteed across Blender versions.

Source-edit proof: pass a fresh isolated absolute output directory after `inspect_sources.py --`. The script reopens the shipped source, lowers only diffuser underside vertices 1 mm, changes emission RGB from (0.8,0.73,0.55) to (0.3,0.25,0.18), and saves a separate source. Run the copied generator there with `--export-source --skip-render`, then `verify_source_edit.mjs /isolated/directory`. The original shipped source/export and all other component bounds remain unchanged.

## Rights

Original geometry and materials authored for Blender-3D-Gallery. Reuse in the owner's projects is authorized. Public redistribution terms have not been specified. Public download remains disabled. No remote push, PR, merge, release or deployment is asserted.

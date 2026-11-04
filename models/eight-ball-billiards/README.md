# Eight-ball billiards asset pack

Original, unbranded, meter-scale 3D assets created procedurally with Blender 5.1.2. The gallery build includes the independently selectable GLBs and the complete scene; the editable Blender source remains in the repository. No redistribution license has yet been selected.

## Contents

- `scene.blend`: editable Blender source, with asset roots named `ASSET_*` and a separate `STUDIO` group for the preview camera, floor and lighting.
- `generate.py`: source used to recreate the scene, render and GLB exports.
- `preview.webp`: 1600 × 1200 preview of the modeled scene.
- `exports/billiards-scene.glb`: complete scene without the studio objects.
- `exports/ball_00.glb` through `ball_15.glb`: cue ball and numbered balls, each centered on its own origin.
- `exports/table.glb`, `cue_01.glb`, `cue_02.glb`, `triangle_rack.glb` and `chalk.glb`: separately reusable assets. Individual exports are positioned at their asset-root origin; the table origin is at floor level.

The outside table dimensions are approximately 2.54 × 1.40 m, ball diameter 57.15 mm and cue length 1.47 m. Balls use geometry for the number marks, attached to each ball's root; the numbering is on one side only. Materials use glTF-compatible Principled BSDF base color, metallic and roughness values; no external textures are required. UV layers are present, but a dedicated non-overlapping texture atlas has not been produced. The design is simplified and uses clean, untextured surfaces rather than photographic wood grain, cloth fibers or wear.

## Reproduce

From the repository root, with Blender 5.1.2 and `cwebp` installed:

```sh
blender --background --factory-startup --python models/eight-ball-billiards/generate.py
cwebp -q 88 models/eight-ball-billiards/preview.png -o models/eight-ball-billiards/preview.webp
```

The generator writes and replaces the artifacts in this directory. It also produces the intermediate `preview.png` and Blender may create a `scene.blend1` backup when overwriting. Inspect any existing work before regenerating.

## Verification performed

- Blender mesh inspection: 99 asset meshes, 24,652 triangles, UV layers on all meshes, no non-manifold edges or zero-area faces detected. Mesh-level checks do not prove that separate meshes never intersect.
- Six pocket liners, sixteen ball roots and numeral meshes 1–15 were counted in the Blender source. The 15-ball number was also inspected in a close-up render. Markings are on one pole only and will not remain visible at every rotation.
- Khronos glTF Validator checked all 22 GLBs: zero errors and zero warnings. Informational messages were present.
- The complete scene loaded and rendered in desktop Chrome through Three.js GLTFLoader with WebGL2; 106 mesh primitives and materials were observed. Mobile devices, other engines and physics behavior were not tested.
- Preview inspected against the generated scene. The geometry and materials are intentionally lightweight and unbranded; redistribution terms remain to be decided.

## Independent export and catalog maintenance

The saved source contains 21 `ASSET_*` roots. To export them without changing the source file, provide a destination directory:

```sh
blender --background models/eight-ball-billiards/scene.blend --python scripts/export-selected-assets.py -- /tmp/billiards-exports
npm run validate:assets
```

Each individual export contains only its asset root and children, with the root at the origin. The table origin is at floor level; balls use their centers. The full scene preserves the assembled positions and the original `?model=eight-ball-billiards` link.

Card thumbnails were generated from the corresponding source asset, using `scripts/render-asset-thumbnails.py` with Blender Workbench, then converted to WebP with `cwebp`. The catalog at `models/catalog.json` maps identities to exports and thumbnails. Triangle counts and file sizes are calculated from the GLBs at build time.

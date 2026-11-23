# Mall Outside Corner Floor 2 m

This 2 × 2 m floor turns a double champagne border through 90° around an inset eucalyptus terrazzo ribbon. Its 500 mm ivory pavers, flush grout, 70 mm precast backing, bond course and eased underside match the [straight floor](../mall-floor-module-2m/README.md). It corresponds to shopping mall registry item `MALL-STR-002`. [Studio view](previews/mall-floor-corner-2m.webp) · [Editable source](sources/mall-floor-corner-2m.blend)

## Placement and border profile

The underside centre is the origin. The GLB spans X/Z = −1 to +1 m and Y = 0 to 0.100 m. Set the root to Y = −0.100 m for a finished floor at world Y = 0. The decoration runs along +X and +Z. In Blender these edges are +X and −Y. Rotate the whole module in 90° increments for the other orientations.

Distances below run inward from the nearest decorated outer edge. All surfaces finish at the same elevation. An external edging kit can abut the module at X = 1 m or Z = 1 m. Its footprint lies outside this floor.

| Inward distance | Wearing surface |
| --- | --- |
| 0–25 mm | Original ivory and grout outer lip |
| 25–53 mm | 28 mm brushed champagne arm |
| 53–103 mm | 50 mm cut eucalyptus terrazzo |
| 103–117 mm | 14 mm brushed champagne arm |
| Beyond 117 mm | Original ivory pavers and flush grout |

Each champagne strip is cut on the GLB X = Z diagonal. Its front and right arms share the physical diagonal edge. The narrow and wide junctions together measure 59.397 mm along the diagonal. Both ends meet a straight floor at the same height. A continuing decorative border requires the same profile on the adjoining module.

## Geometry and distance variants

| Variant | Triangles | Material draws | Bytes | Finish |
| --- | ---: | ---: | ---: | --- |
| [L0](exports/mall-floor-corner-2m.glb) | 1,344 | 7 | 173,580 | Segmented paver corners, cut metal arms and independently textured ribbon |
| [L1](exports/mall-floor-corner-2m-lod1.glb) | 832 | 7 | 154,120 | Simplified paver corners and the same cut border geometry |
| [L2](exports/mall-floor-corner-2m-lod2.glb) | 36 | 1 | 67,088 | Registered colour and metallic/roughness atlases on the original slab profile |

[Mid-distance studio view](previews/mall-floor-corner-2m-lod1.webp) · [Distant studio view](previews/mall-floor-corner-2m-lod2.webp). L2 softens the narrow inner line at close range. Choose a distance cutoff based on screen size and the intended hardware.

The source has one welded mesh per level. L0 and L1 include named face materials and vertex selections for each champagne arm and the stone ribbon. The border geometry replaces the underlying top faces. In Blender Edit Mode, select a material slot and use **Select** to edit its faces. The L2 atlas has its own colour and material response.

## Checks and reproduction

Blender reopens the source and reimports all three GLBs. The test checks source manifold edges, 4 m² of correctly oriented top triangles, 2,401 surface rays and four probes outside the footprint per level. L0 and L1 each pass another 64 probes spanning the two sides of every band boundary. The verifier measures the metal and stone areas and the two shared diagonal cuts. L2 is checked using 80 exported mesh and texture coordinates for stone, both strips and both arms. All three GLBs passed Khronos glTF Validator with zero errors and warnings. [Measured source and export results](reports/source-reimport.json) · [Export hashes and metadata](metadata/mall-floor-corner-2m.json)

From the repository root, run the checks with Blender 5.1.2 and the project's Node dependencies.

```sh
blender --factory-startup -b -Y --python-exit-code 1 \
  --python models/mall-floor-corner-2m/verify_blender.py
node models/mall-floor-corner-2m/verify.mjs
```

The following rebuilds the three GLBs from saved edits and renders each imported export. Run it in a copy to retain the reviewed export files.

```sh
blender --factory-startup -b -Y --python-exit-code 1 \
  --python models/mall-floor-corner-2m/generate.py -- --export-source
```

For fresh procedural authoring, place the generator in an empty directory beside the straight floor and omit `--export-source`, or pass `--straight-source /path/to/mall-floor-module-2m.blend`. Use `--skip-render` when only the GLBs are needed. Clean re-export of the reviewed source reproduced all three GLBs byte for byte.

## Provenance

The generator derives its substrate and seeded ivory finish from the owner's Blender-3D-Gallery straight floor. It adds the coloured cut-stone ribbon, two metal lines, their mitres and the distant surface atlases. All required surface images are packed in the saved source and embedded in the exports. Owner-project reuse is authorized. Public redistribution terms are unspecified. The Gallery follows the straight floor's disabled-download setting.

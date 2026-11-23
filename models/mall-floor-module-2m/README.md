# Mall Straight Floor Module 2 m

A 2.00 × 2.00 × 0.10 m straight floor for the modular mall registry item `MALL-STR-001`. Sixteen honed ivory terrazzo pavers sit in flush warm-grey joints over a precast slab. The surface uses the [original seed 421 project artwork](../mall-floor-tile/textures/terrazzo-original.png) at the existing floor's stone-to-texture scale. [Studio view](previews/mall-floor-module-2m.webp) · [Editable Blender source](sources/mall-floor-module-2m.blend)

## Placement

The source uses metres and Blender Z up. The GLB uses metres and Y up. The origin is the underside centre. For a finished floor at world Y = 0, place this module at Y = −0.100 m and the [1.2 m floor](../mall-floor-tile/README.md) at Y = −0.030 m. Each new tile extends from −1 to +1 m along X and Z and has a 2 mm half-joint at each edge. Four quarter turns use the same footprint. Keep scale at one.

Set neighbouring 2 m centres exactly 2 m apart. For a straight mixed edge 6 m long, three new modules meet five existing modules. The surface of both stone finishes reaches the same world elevation. The original tile's grout sits 1 mm below that elevation. The underside includes a 2 mm bevel, and the vertical slab edge exposes a 3 mm bond course above the 70 mm precast base.

## Three exported levels of detail

| Level | Geometry and appearance | Triangles | Material draws per instance | GLB bytes |
| --- | --- | ---: | ---: | ---: |
| [L0](exports/mall-floor-module-2m.glb) | Five geometric segments on each 6 mm radius paver corner, flush grout and original 512 px aggregate texture | 942 | 4 | 154,572 |
| [L1](exports/mall-floor-module-2m-lod1.glb) | One chamfer at each paver corner, shared grout and original surface materials | 430 | 4 | 135,112 |
| [L2](exports/mall-floor-module-2m-lod2.glb) | Single baked 512 px atlas for the top, vertical courses and underside. The perimeter retains the bevel and bond course | 36 | 1 | 48,888 |

Compare the [mid-distance render](previews/mall-floor-module-2m-lod1.webp) and [distant render](previews/mall-floor-module-2m-lod2.webp) with the studio view. All three use the same camera and lights and render the corresponding imported GLB. The far surface uses a single roughness and has less fine aggregate detail at close range. Choose a switching distance using the intended scene and device.

## Verification

Khronos glTF Validator reported zero errors and warnings for each self-contained GLB. Blender reopened the saved source and separately imported all three GLBs. Each level delivered a 4 m² top, with 2,401 vertical probes hitting the wearing surface at 0.100 m including the four sides and corners. Four probes beyond the module missed. The verifier also checks manifold source geometry, upward top triangles, edge bounds and the warm finish colour in the exported textures. [Reimport report](reports/source-reimport.json) · [Measured sizes and hashes](metadata/mall-floor-module-2m.json)

A clean re-export of the saved source on Blender 5.1.2 produced byte-identical GLBs for all three levels. In an isolated copy, changing the precast material roughness from 0.78 to 0.41 reached the L0 and L1 exports. The distant mesh uses its own baked material. This geometry is a digital asset. Physical device performance and construction suitability are outside these measurements.

## Reproduce

From the repository root, use Blender 5.1.2 and the locked Node dependencies. The following checks read the existing files. The Blender check rewrites the source reimport report.

```sh
blender --factory-startup -b -Y --python-exit-code 1 \
  --python models/mall-floor-module-2m/verify_blender.py
node models/mall-floor-module-2m/verify.mjs
```

To regenerate from the editable source, run this command on a copy of the asset directory. L0, L1 and L2 are editable meshes in the same Blender file. Only L0 is initially visible.

```sh
blender --factory-startup -b -Y --python-exit-code 1 \
  --python models/mall-floor-module-2m/generate.py -- --export-source --lod-previews
```

For a fresh procedural build, copy the generator to an empty directory alongside the existing mall-floor-tile folder and omit `--export-source`. Alternatively pass `--texture` followed by the path to `terrazzo-original.png`. The generator preserves any existing source by requiring an empty destination for fresh builds.

## Provenance

Original geometry and materials authored for Blender-3D-Gallery. Both texture levels derive from the project's original seeded terrazzo artwork. Owner-project reuse is authorized. Public redistribution terms are unspecified. The Gallery entry follows the existing floor's disabled-download setting.

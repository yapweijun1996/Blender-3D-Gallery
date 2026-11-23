# Mall ceiling perimeter infill

One 1.20 × 0.80 m perimeter cassette completes a 2.00 m roof width with the [original 1.20 m square cassette](../mall-ceiling-panel/README.md). The first 600 mm field continues the existing grid. A 200 mm field and a 12 mm half flange finish the wall edge. The thumbnail shows the underside of the exported GLB. [Studio render](previews/mall-ceiling-infill-800.jpg)

## Fit

Use the unscaled root `ASSET_MallCeilingInfill800`. In glTF, X spans −0.60 to +0.60 m, Z spans −0.40 to +0.40 m, and Y=0 is the underside of the grid. The standard cassette mates to the −Z side. The shorter panels face the wall at +Z. Two neighbouring infills repeat at 1.20 m pitch along X. Place the original and new cassette roots at Z=−0.40 and +0.60 m respectively to cover Z=−1 to +1 m.

| Contact or component | Measured GLB geometry |
| --- | --- |
| Mating edge | `CONNECTOR_ZN` lies at (0, 0.018, −0.40). It meets the original cassette's `CONNECTOR_YN`, which points along glTF +Z. |
| Wall edge | `CONNECTOR_ZP` lies at (0, 0.018, +0.40). The wall-side rail meets a 2.80 m wall top when the cassette root is at Y=2.80. |
| Neighbouring infills | `CONNECTOR_XN` and `CONNECTOR_XP` sit at X=±0.60, Y=0.018, Z=0. Each side contributes a 12 mm flange. |
| Panels | `PANEL_3` and `PANEL_4` are 576 × 576 mm. `PANEL_1` and `PANEL_2` are cut to 576 × 176 mm. All are 16 mm thick with an underside 8 mm above the rail face. |
| Rails and suspension | The original T section retains its 4 mm flange thickness, 3 mm web and 32 mm overall height. The two hanger pairs are centred at X=±0.48 m, on Z=+0.20 and −0.391 m. Their upper plates reach Y=0.36 m. The plates nearest the mating edge stop 3 mm inside the footprint. |

The model represents a decorative installation. The contact measurements describe its geometry. Load ratings, acoustic performance, fire safety and electrical performance require separate assessment.

## Source and validation

The [editable Blender source](sources/mall-ceiling-infill-800.blend) contains 25 closed mesh components, their native bevels, four connectors and the packed original 256 × 256 mineral-fibre texture. The generator cuts the stock mesh ends before the bevel and crops the short panels' underside UVs to preserve the texture scale. The untextured steel top plates use only position and normal attributes. The generator reopens the saved source before exporting so Blender evaluates the current bevel geometry.

The GLB contains 1,724 triangles and 29 material primitives in 139,600 bytes. Khronos validation returned zero errors and warnings. A fresh build and an export from the saved source produced the same SHA-256. In a separate edited copy, lowering one panel face by 1 mm produced a 7 mm finished recess in the reimported GLB. The adjacent panel retained its 8 mm recess. The same export retained the edited finish roughness of 0.71. [GLB measurements](reports/geometry.json) · [Source and edited-export verification](reports/source-reimport.json) · [Repeatability across checkouts](reports/relocation.json)

From the gallery root, with Blender 5.1.2 and the locked Node packages installed, run the following commands. The first exports changes already saved in the Blender source. Use `--rebuild` in its place to regenerate the cassette from the original sibling asset. The studio thumbnail is rendered from the reimported GLB. Pass `--skip-render` for a geometry-only export.

```sh
asset=models/mall-ceiling-infill-800
blender -b --factory-startup -Y -t 4 --python-exit-code 1 -P "$asset/generate.py" -- --export-source
blender -b --factory-startup -Y -t 2 --python-exit-code 1 -P "$asset/verify_source.py"
node "$asset/verify.mjs"
```

The original editable cassette, all materials and the packed mineral-fibre artwork belong to Blender-3D-Gallery. This adaptation reuses them under the owner's project-reuse terms. Public download and redistribution terms remain unspecified. [Source attribution and hashes](metadata.json)

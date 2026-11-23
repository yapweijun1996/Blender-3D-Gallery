# Mall wall corner · 2 m arms

This 90° inside corner continues the original [2 m straight limestone wall](../mall-wall-module-2m/README.md). The backing, dark-bronze skirting, champagne lip and top trim turn through a 45° miter. Two courses of stone cladding follow both arms. The source uses the straight wall's actual finish profiles and packed texture. [Studio render](previews/mall-wall-corner-2m.jpg) · [All three exported levels](reports/levels.png)

## Fit and orientation

The root is the intersection of the two wall centrelines at finished floor elevation. Each arm measures **2.00 m from this centre to its end**. The wall is 150 mm deep and 2.80 m high. In glTF, Y is up, the public sides face +Z along the west arm and −X along the return. This matches the orientation of the earlier [1.2 m corner](../mall-wall-corner/README.md).

| Connection or limit | Local glTF X, Y, Z (m) |
| --- | --- |
| West end (`CONNECTOR_Left_LOD0`) | −2, 0, 0 |
| Return end (`CONNECTOR_Return_LOD0`) | 0, 0, +2 |
| Minimum visible bounds | −2, 0, −0.075 |
| Maximum visible bounds | +0.075, 2.80, +2 |

The outer plan envelope is **2.075 × 2.075 m**. For a complete test run, place straight roots at (−3, 0, 0) and (0, 0, 3). Rotate the second straight −90° about glTF Y. The two detailed levels have matching 2 mm half-reveals at their ends, producing 4 mm vertical installed joints. The 120 mm plinth and 10 mm horizontal shadow bands continue around the elbow. Each level has its own matching connector suffix.

The center miter uses a pair of arm meshes for each continuous finish. Matching vertices form one closed surface after assembly. Both internal cap faces are omitted. Each mesh has a narrow planar bounding box, which keeps the open aisle clear for the mall visitor collision controller. An earlier one-piece backing enclosed the aisle in its bounding box.

## Model files

The [Blender source](sources/mall-wall-corner-2m.blend) contains three editable collections. The full-detail stone panels on the two arms can be edited independently. Original project limestone artwork is packed into the source and close GLB. Its external reference points to the [straight wall texture](../mall-wall-module-2m/sources/honed-limestone.png).

| Level | Appearance | Triangles | Draw calls | Bytes |
| --- | --- | ---: | ---: | ---: |
| [Close](exports/mall-wall-corner-2m.glb) | 16 eased, textured stone faces and full metal profile | 1,068 | 24 | 206,328 |
| [Middle](exports/mall-wall-corner-2m-lod1.glb) | Eight flat stone panels per arm and simplified trim | 264 | 8 | 20,708 |
| [Distant](exports/mall-wall-corner-2m-lod2.glb) | Two closed-in-assembly finish bands with vertex colours | 68 | 2 | 6,960 |

## Evidence

- All three GLBs passed Khronos validation with zero errors and warnings. The nine combinations of straight and corner detail levels produced 1,080 terminal surface hits across both installed joins. Their end planes meet at zero measured gap. A further 54 probes checked the inside crease, outside crease and panel returns. Scanning actual triangles found zero internal miter-cap triangles and zero triangles projecting into the opposite wing. Reversing a straight or displacing it 5 mm reproduced the expected errors. [Geometry report](reports/geometry.json)
- Blender reopened the source, matched the packed original image and inspected every arm. The only intentional border edges lie on the shared miter. Each paired finish group forms a closed positive-volume surface. Bounds and volumes matched after clean GLB reimport. [Source and reimport](reports/source-reimport.json)
- Chromium loaded all three exact files, decoded the embedded 512 × 512 image, measured their draw counts and compared their silhouettes at one fixed camera. [Browser results](reports/browser.json)
- A second build from the authored straight source and a fresh export from the saved corner source produced the same three GLBs byte for byte. [Rebuild record](reports/rebuild.json)

The verified arrangement uses a 90° turn and the 2 m straight family. Mixed 1.2 m/2 m wall profiles require a separate transition. Target-device performance and construction, fire, or acoustic ratings have separate acceptance requirements. All geometry, materials, texture and previews originate in the owner project. Public download and redistribution terms are unspecified.

## Reproduce

Run at the repository root with Blender 5.1.2, the project dependencies and Playwright Chromium.

```sh
asset=models/mall-wall-corner-2m
blender -b --factory-startup -Y -t 4 --python-exit-code 1 -P "$asset/generate.py" -- --export-source
blender -b --factory-startup -Y -t 2 --python-exit-code 1 -P "$asset/inspect_source.py"
node "$asset/verify.mjs"
node "$asset/verify-browser.mjs"
```

`--export-source` preserves the saved editable corner. To rebuild procedurally in a new directory, copy `generate.py` there and pass `--straight-dir` pointing to the original straight asset. Replacing an existing source requires `--rebuild`. Add `--skip-render` for export-only reproducibility checks.

# Mall wall module · 2 m

An original straight interior wall for the provisional `MALL-STR-010` dimensions. Four half-metre bays contain two courses of honed limestone cladding. A folded dark-bronze plinth, narrow champagne lip and matching crown finish the public side. The existing [1.2 m mall wall](../mall-solid-wall/README.md) informed the material palette. This family has its own panel layout, metre dimensions, mesh sources and original packed artwork.

## Assembly

The wall is **2.00 m wide, 0.15 m deep and 2.80 m high**. Place the root at the finished floor elevation. In glTF the origin is ground centre, Y is up and +Z faces the corridor. Bounds are X −1.00 to +1.00, Y 0 to 2.80 and Z −0.075 to +0.075 m. In Blender the public side faces −Y.

Place successive roots 2.00 m apart along local X. The exported connector empties are at X −1 and +1 m, Y=Z=0. Within each file their names start with `CONNECTOR_Left` and `CONNECTOR_Right` and end with the level. The backing, plinth and crown meet at flat end planes. Two adjacent 2 mm half-reveals give the installed cladding its 4 mm vertical joint. The finished plinth height is 120 mm. The crown starts at 2.734 m. The 1.2 m family uses a different height, thickness and panel profile. A direct mixed-family wall-to-wall joint needs a designed return or transition.

## Source and detail levels

The [editable Blender source](sources/mall-wall-module-2m.blend) contains the `LOD0`, `LOD1` and `LOD2` collections. Only LOD0 is shown initially. The original [512 px limestone image](sources/honed-limestone.png) is packed into the source and the close GLB. The other levels use texture-free finishes. The studio camera, lights and floor stay outside the model exports. [Studio render](previews/mall-wall-module-2m.jpg) · [Three.js comparison](reports/levels.png)

| File | Geometry | Triangles | Draw calls | Bytes |
| --- | --- | ---: | ---: | ---: |
| [Close](exports/mall-wall-module-2m.glb) | Eight individually editable eased stone slabs, return edges, full plinth profile and brass lip | 548 | 12 | 165,976 |
| [Middle](exports/mall-wall-module-2m-lod1.glb) | Eight flat-faced slabs in one mesh, simpler plinth, solid-colour limestone | 140 | 4 | 11,320 |
| [Distant](exports/mall-wall-module-2m-lod2.glb) | Single closed backing and trim silhouette with vertex-coloured finish bands | 44 | 1 | 4,256 |

## Verification

- Blender reopened all three source collections, checked closed positive-volume meshes, and compared volume and bounds after reimporting each GLB. The packed image uses a relative path and matches the original artwork byte for byte. [Source and reimport](reports/source-reimport.json)
- All three GLBs passed Khronos validation with zero errors and zero warnings. Against two end joints per level, 384 actual Three.js ray hits checked the back plane, skirting, crown, paired stone faces and, on the two detailed levels, the recessed joints. The measured end-plane gap was zero. An introduced 5 mm translation produced an open crack, and an outward-facing wall produced a measurable profile step. [Geometry and seams](reports/geometry.json)
- Chromium rendered the three exact SHA-256 digests and decoded the embedded image at 512 × 512. At one fixed camera, the middle and distant silhouettes each overlapped the close model by more than 99.89%. The comparison measures these three still views. Device frame rates, LOD switching policy, corners and other wall systems need scene-specific evidence. [WebGL results](reports/browser.json)
- Exporting the saved source and building again in a second directory produced the same bytes at all three levels. [Rebuild verification](reports/rebuild.json)

Original geometry, material settings, texture and render created for Blender-3D-Gallery. Public download and redistribution terms are unspecified. The model depicts a fictional interior finish. Structural, acoustic and fire ratings require separate engineering assessment.

## Reproduce

From the repository root, use Blender 5.1.2, the project's Node dependencies and Playwright Chromium.

```sh
asset=models/mall-wall-module-2m
blender -b --factory-startup -Y -t 4 --python-exit-code 1 -P "$asset/generate.py" -- --export-source
blender -b --factory-startup -Y -t 2 --python-exit-code 1 -P "$asset/inspect_source.py"
node "$asset/verify.mjs"
node "$asset/verify-browser.mjs"
```

`--export-source` exports the saved collections and renders the editable scene. For a fresh procedural build, copy `generate.py` into an empty asset directory and run it there with the same Blender options. An existing source file requires an explicit `--rebuild` before procedural generation can replace it. `--skip-render` omits the JPEG during repeated export checks.

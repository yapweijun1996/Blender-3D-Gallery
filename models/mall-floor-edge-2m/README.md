# Mall floor edge · 2 m trim kit

A 60 mm champagne-metal cap and a 100 mm deep bronze fascia finish the outside of the [2 m mall slab](../mall-floor-module-2m/README.md). The kit contains one flat-ended [straight strip](exports/mall-floor-edge-2m.glb) and one [matched 45° mitre pair](exports/mall-floor-edge-2m-mitre.glb). Both use the same cross-section, including a flush 1.5 mm bronze line in the cap, a returned metal nose and a recessed channel along the lower fascia. Small bronze buttons attach along the front face. [Straight studio render](previews/mall-floor-edge-2m.jpg) · [Mitre studio render](previews/mall-floor-edge-2m-mitre.jpg)

## Fit the edge

All geometry uses metres. glTF Y is up. Put the floor's underside-centre root at Y = −0.100. Place these trims at Y = 0. The full 60 mm width of the top cap sits at finished floor height. The bottom is at −0.100 m.

| Part | Root and local envelope |
| --- | --- |
| Straight | Top-centre pivot. X −1 to +1, Z −0.03 to +0.03. The decorative fascia faces +Z. On a tile centred at the origin, use root (0, 0, 1.03). |
| Outside mitre | Top pivot over the centre of the [outside corner tile](../mall-floor-corner-2m/README.md). Both arms connect at the square ends at X = −1 or Z = −1. They wrap the +Z and +X tile faces. Their outer bounds span −1 to +1.06 on both axes. |
| Continuations | Place a straight at (−2, 0, 1.03) with its original orientation. Place a second straight at (1.03, 0, −2), yaw +90° about Y. The connector centres are (−1, 0, 1.03) and (1.03, 0, −1). |

The diagonal runs along X = Z from (1, 0, 1) to (1.06, 0, 1.06). Each arm is independently editable in the [Blender source](sources/mall-floor-edge-2m.blend). The arm surfaces meet at the shared diagonal edges to enclose the section. Internal cap faces are omitted there. The outside turn uses both full-length arms. Placing two more ordinary strips around the same tile would duplicate the corner geometry.

The [1.2 m straight trim](../mall-floor-edge-trim/README.md) and [old mitre](../mall-floor-mitred-trim/README.md) have 30 mm depth. The new straight uses a fresh section to cover the 100 mm slab edge. It retains the older family's warm metal and dark support palette.

## Detail levels

Profiles repeat at the same pitch and keep the same outer face, cap, keyline and underside at every level, including mixed-level joins. Close inspection shows button rims with hexagonal recesses. The middle level simplifies the buttons to six sides. The distant level removes the buttons and keeps the cap/bronze separation in vertex colours, with one material per arm. [Rendered level comparison](reports/levels.png)

| Level | Straight triangles / draws / bytes | Mitre pair triangles / draws / bytes |
| --- | ---: | ---: |
| Close | [296 / 3 / 15,968](exports/mall-floor-edge-2m.glb) | [562 / 6 / 30,176](exports/mall-floor-edge-2m-mitre.glb) |
| Middle | [128 / 3 / 9,200](exports/mall-floor-edge-2m-lod1.glb) | [226 / 6 / 16,156](exports/mall-floor-edge-2m-mitre-lod1.glb) |
| Distant | [64 / 1 / 5,524](exports/mall-floor-edge-2m-lod2.glb) | [98 / 2 / 8,956](exports/mall-floor-edge-2m-mitre-lod2.glb) |

## Verification

- All six actual GLBs passed Khronos validation with zero errors and warnings. Across both square joints, all nine straight/mitre LOD pairings produced zero measured gap. In 1,512 top, underside and fascia probes, the largest step was 0.057 μm. An additional 66 rays checked both sides of the three diagonal junctions. The triangle scan found zero internal cap triangles or triangles from one arm projecting across the miter. [Assembly results](reports/assembly.json)
- Every mitre level was placed against both the original 2 m floor GLB and the 2 m corner tile GLB. The 768 sampled hits compared the finished floors, top caps and lower slab-to-fascia interfaces. A deliberate 5 mm translation opened a visible through-gap. A separate check confirmed that the short legacy section leaves the lower fascia exposed. [Tile and trim results](reports/assembly.json)
- Blender reopened the source and compared volume and bounding limits after six clean GLB reimports. The only individual arm borders are on the shared 45° miter. Welding that seam in a temporary checking copy gives closed, positive-volume geometry. [Source and reimport](reports/source-reimport.json)
- Chromium rendered all six files with matching hashes and counted their actual WebGL draws. At the checked fixed views, each reduced level retained the close model's silhouette. [Browser results](reports/browser.json)
- A fresh procedural build and an export of the saved Blender source reproduced all six GLBs byte for byte. [Rebuild report](reports/rebuild.json)

The measured assembly covers straight continuations and this 90° outside turn. Other angles, inside turns, physical-device performance and installation require separate assessment. The geometry, materials and studio renders are original work for Blender-3D-Gallery. Public redistribution and download terms are unspecified.

## Reproduce

Use Blender 5.1.2 and the gallery's Node and Playwright dependencies from the repository root.

```sh
asset=models/mall-floor-edge-2m
blender -b --factory-startup -Y -t 4 --python-exit-code 1 -P "$asset/generate.py" -- --export-source
blender -b --factory-startup -Y -t 2 --python-exit-code 1 -P "$asset/verify_blender.py"
node "$asset/verify.mjs"
node "$asset/verify-browser.mjs"
```

`--export-source` reads the six saved collections and preserves the editable source. For a fresh build, copy the generator to an empty asset directory. Replacing an existing source procedurally requires `--rebuild`. Add `--skip-render` for repeated export checks.

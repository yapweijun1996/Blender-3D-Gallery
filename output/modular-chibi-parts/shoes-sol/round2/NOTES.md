# Sneaker pair v2

Round 2 passes the supplied vertex and triangle intersection checks for all
eight cases. A denser reimport test also passes at 674 samples, including run
frame 4. The remaining issue is visible skin through local underside relief
openings when a lifted foot exposes the sole.

## Deliverables

- [make_shoes_v2.py](make_shoes_v2.py) builds the editable
  [Blender scene](shoes_sneaker_v2.blend) and the [GLB](shoes_sneaker_v2.glb).
- [Vertex checker output](motion_check.txt) and [JSON](motion_check.json).
- [Triangle checker output](motion_check_tri.txt) and [JSON](motion_check_tri.json).
- [Dense motion and floor check](dense_check.json) and
  [Khronos validator report](validator.json).
- [Standalone preview](sneaker_preview.png) and motion renders for
  [walk](walk.png), [run](run.png), [wave](wave.png), and [jump](jump.png).
- Close-ups from the exported mesh on the master body. See the
  [run frame 4 toe view](run_frame4_toe.png), its
  [underside view](run_frame4_underside.png), and the
  [walk frame 19 toe view](walk_frame19_toe.png).

## Geometry and rig

The new outer profile retains the purple upper, ivory toe and welt, purple
tread, two lace bands, lateral stars, and rolled collars. The nominal welt
height is 18 mm. The tread has planar contact areas and rises at the toe and
heel where the supplied gait requires clearance. The build checks a
tessellated tread against posed foot triangles and refines long crossing
diagonals locally. Main midfoot weights favor Foot. Every sampled front-sole
and toe-cap vertex past Y = −95 mm favors ToeBase. The collars blend toward
Leg. Each mesh vertex uses one to three influences. The master pose bones
retain their quaternion rotation modes.

Median rest signed clearances are about 7.6 mm for the outer purple upper
and 7.4 mm for the lining. The toe-cap samples range from 4.5 to 11.2 mm.
The sole samples have medians of 2.7 mm (left) and 2.8 mm (right), with
smaller margins at the closest floor contacts. Local underfoot spacing
therefore falls short of the requested 4–8 mm. The tread has relief openings
and the 18 mm welt is a nominal exterior dimension.

The GLB has one sneaker mesh, five material primitives, one skin with 65
joints, and zero embedded animations or textures. The joint names, order
and inverse-bind data match the round-one GLB byte for byte. The pair has
**3,480 triangles**. The GLB is **247,684 bytes** and the Blender scene is
**201,891 bytes**. Khronos glTF Validator 2.0.0-dev.3.10 reports **0 errors
and 0 warnings**.

## Vertex checker RESULT

| Case | Max vertices inside | Min signed distance (m) |
| --- | ---: | ---: |
| rest | 0 | 0.000536525 |
| walk | 0 | 0.0005 |
| run | 0 | 0.0005 |
| wave | 0 | 0.0005 |
| jump | 0 | 0.0005 |
| idle | 0 | 0.0005 |
| nod | 0 | 0.0005 |
| dance | 0 | 0.0005 |

## Triangle checker RESULT

| Case | Max overlap pairs | Min signed distance (m) |
| --- | ---: | ---: |
| rest | 0 | 0.000536525 |
| walk | 0 | 0.0005 |
| run | 0 | 0.0005 |
| wave | 0 | 0.0005 |
| jump | 0 | 0.0005 |
| idle | 0 | 0.0005 |
| nod | 0 | 0.0005 |
| dance | 0 | 0.0005 |

The triangle checker reproduced 90, 98 and 225 overlap pairs for v1 in
rest, walk and run. The two supplied checkers use different sample schedules
and round animated distances to four decimal places. The supplemental test
checks every quarter frame of walk and run, and every integer frame of the
other clips. It found zero interior vertices and zero triangle overlaps at
every sample. The closest vertex was 0.000535289 m outside the body at
run frame 5.5. Run frame 4 was included in the dense pass.

## Floor

The contact plane is nominally Z = 0. The export adds a 0.2 µm Z offset
to counter floating-point error when Blender reimports and skins the mesh.
The smallest evaluated rest heights are +0.085 µm left and +0.093 µm
right. In walk and run, floor margin is each shoe's lowest vertex minus
the lesser of Z = 0 and its corresponding foot's lowest vertex.

| Clip | Side | Worst frame | Minimum margin (m) |
| --- | --- | ---: | ---: |
| walk | Left | 40 | +0.000003017 |
| walk | Right | 27 | +0.000003047 |
| run | Left | 24.5 | +0.000003099 |
| run | Right | 2.5 | +0.000003106 |

## Open visual requirement

The left master foot already reaches Z = 0 at rest. Other regions of the
toe and heel skin sit within 0.5 mm of that plane. A continuous 12–20 mm
slab starting on the floor and spanning those areas would pass through the
skin. This build preserves ground contact with planar tread patches and
retains openings at locations where the fitted tread would intersect the
posed foot. Skin is visible through those openings in underside or steeply
tilted views, including run frame 4 and walk frame 19. This round clears
the geometry intersection gate. A fully opaque sole and 4–8 mm underfoot
clearance remain open. The independent reviewer observed a clear right toe
from the side at run frame 4, an exposed forefoot patch from underneath at
the same frame, and skin through the toe and lower tread at walk frame 19.
The lace adjustment removed the raised white spikes in the previous preview.
A small break in the lace silhouette remains in the run close-up.

## Rebuild and provenance

Run from this directory with Blender 5.1.2 using the supplied guarded
launcher. The builder reads the master scene, the motion GLB, and the v1
GLB for the bind-data comparison. The default command writes both assets,
the checker reports, dense measurements and all PNGs. Use `-- --assets-only`
to rebuild just the assets or `-- --qa-only` to check an existing v2 GLB.

```sh
blender -b -noaudio --python-exit-code 1 --python make_shoes_v2.py
```

The headless runner uses CPU Cycles because Workbench aborts on this host.
It substitutes the render setup in memory and runs the supplied geometry
checks, sampling, camera, and JSON serialization as given. The one local
Node invocation ran the repository's installed Khronos validator against
the final GLB.

```sh
node -e 'const fs = require("node:fs"); const v = require("../../../../node_modules/gltf-validator"); v.validateBytes(new Uint8Array(fs.readFileSync(process.argv[1])), {uri: process.argv[1]}).then(r => { fs.writeFileSync("validator.json", JSON.stringify(r, null, 2) + "\n"); process.exitCode = Number(!!(r.issues.numErrors || r.issues.numWarnings)); });' shoes_sneaker_v2.glb
```

Final GLB SHA-256  
`87098c7a0544bf83fb8c6ed4cc89c866c93af91891a12ef60dc3cbf159e1f608`

Master body SHA-256  
`0339318b375836ab8891e49bda178da7e6f115e012e83385d9f8850949a7bd6f`

Motion GLB SHA-256  
`ffccda1ba2a50eb10948853e03d17f0d095cd9b953d644c03c4fb9cb95529410`

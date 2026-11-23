# Sneaker pair, round 3

[Blender source scene](shoes_sneaker_v3.blend) · [GLB](shoes_sneaker_v3.glb) ·
[Rebuild script](make_shoes_v3.py) · [Static preview](sneaker_preview.png)

## Geometry and rig

The rounded sole outline comes from the projected foot, with a bevel around
the toe and heel. The outsole, ivory midsole, rounded toe cap, upper, lining
and underfoot footbed form a continuous mesh on each shoe. The lower upper
is joined directly into the midsole. The footbed is above the tread and
below the plantar skin, leaving an open collar for the ankle.

The [sole geometry check](sole_geometry_check.json) found zero open or
inconsistently oriented shell edges on either shoe. Minimum outline
overhang at rest is 3.573 mm on the left and 3.574 mm on the right,
measured from the projected foot to the lower outsole edge. The sole
and toe cap share vertices through the transition and blend Foot and
ToeBase. The tread and footbed use matched triangulation and share weights
across their thickness. Leg contributes at the heel and collar. The master quaternion
rotation modes were preserved.

The pair has **3,492 triangles**, a maximum of **3 nonzero influences** per
exported vertex and **65 joints**. The joint names, order and inverse bind
matrices match the earlier module. The GLB is **182,844 bytes** and the
Blender scene is **189,630 bytes**. [Asset contract](asset_contract.json) ·
[Khronos glTF Validator, 0 errors and 0 warnings](validator.json)

## Vertex checker RESULT

[Raw log](motion_check.txt) · [JSON](motion_check.json)

| Case | Maximum vertices inside | Minimum signed distance (m) |
| --- | ---: | ---: |
| rest | 0 | 0.003627 |
| walk | 0 | 0.003400 |
| run | 0 | 0.002500 |
| wave | 0 | 0.003600 |
| jump | 0 | 0.003400 |
| idle | 0 | 0.003600 |
| nod | 0 | 0.003600 |
| dance | 0 | 0.003600 |

## Triangle checker RESULT

[Raw log](motion_check_tri.txt) · [JSON](motion_check_tri.json)

| Case | Maximum overlap pairs | Minimum signed distance (m) |
| --- | ---: | ---: |
| rest | 0 | 0.003627 |
| walk | 0 | 0.002500 |
| run | 0 | 0.002700 |
| wave | 0 | 0.003600 |
| jump | 0 | 0.003400 |
| idle | 0 | 0.003600 |
| nod | 0 | 0.003600 |
| dance | 0 | 0.003600 |

The [dense check](dense_check.json) evaluates the exported GLB on the master
at 674 samples, including quarter frames of walk and run. It produced zero
interior vertices and zero triangle overlaps. The lowest distance was
1.213 mm at walk frame 16.25.

## Visual and pixel checks

The front orthographic camera matches round 2's walk.png. Walk 23 and run
12 are the checker render frames. Walk 19 and run 4 reproduce the close-up
review frames. Each frame also has a side view and an underside view from
under the lifted foot.

For the pixel check, every body material emits green. Upper and sole surfaces
emit red and blue, respectively. Cycles CPU uses zero light bounces for the
mask passes. The shoes-only alpha pass defines the silhouette, with enclosed
holes filled and partial antialiasing at the exterior edge excluded. A pixel
inside the silhouette counts as skin if its green channel exceeds 0.02. The
body-only pass checks that green would register at the same location if the
shoe were absent. [Pixel report and camera settings](skin_check.json)

| Frame | Front | Side | Underside | Green pixels inside the underside shoe silhouette | Body-only control pixels |
| --- | --- | --- | --- | ---: | ---: |
| walk 19 | [PNG](walk_frame19_front.png) | [PNG](walk_frame19_side.png) | [PNG](walk_frame19_underside.png) | 0 | 107,808 |
| walk 23 | [PNG](walk_frame23_front.png) | [PNG](walk_frame23_side.png) | [PNG](walk_frame23_underside.png) | 0 | 85,093 |
| run 4 | [PNG](run_frame4_front.png) | [PNG](run_frame4_side.png) | [PNG](run_frame4_underside.png) | 0 | 50,840 |
| run 12 | [PNG](run_frame12_front.png) | [PNG](run_frame12_side.png) | [PNG](run_frame12_underside.png) | 0 | 98,563 |

The front and side masks also see the open collars and projected legs.
The stricter sole-only reading had two antialiased edge cases. In walk 23
side, the conservative hole fill tags one mixed pixel at (419, 130), with
red upper on every side and no blue sole. In run 4 front, one mixed pixel
at (211, 364) lies at the overlapping shoe silhouettes. Its shoes-only
samples already mix red upper and blue sole. Coordinates are zero-indexed
from the upper-left corner. Neither pixel is a resolved skin patch through
the sole. All four underside masks are zero, including mixed green samples.
Round 2 under those same cameras registers **25,167** green silhouette
pixels in walk 19 and **3,290** in run 4. [Round 2 control](round2_skin_check.json)

The final static view and raised-foot renders were visually checked against
the round 2 reference images. The toe no longer terminates in a point or has
the underside notch. Small facets remain visible on the outsole rim and
lace edges at close range.

## Remaining floor constraint

The GLB tread reaches **Z = −6.00 mm at rest**. The master left foot already
has a skin vertex at Z = 0, and the right foot reaches approximately the
same plane. A sole with positive thickness and clearance under those skin
points necessarily extends below the supplied ground plane. This version
prioritizes continuous coverage and keeps the supplied master and motion
inputs intact. The studio preview places its backdrop under the shoes.
The walk clip also reaches Z = −24.10 mm at frame 40, where the same bare
foot is at −9.19 mm. A ground-alignment change would have to raise the assembled character or
change the master foot geometry before rerunning fit and motion QA.

## Reproduction and provenance

Run Blender 5.1.2 with the supplied guarded launcher from the round 3
directory. The default script builds the assets, runs both checkers and
the denser motion check, and renders the QA views. `-- --assets-only`
rebuilds just the assets and `-- --qa-only` checks the existing export.
`-- --baseline-only` reruns the round 2 underside mask comparison after
the round 3 renders exist. The headless checker wrapper uses Cycles CPU
in place of the Workbench render block and leaves geometry, pose sampling,
camera and RESULT generation intact.

| Input | SHA-256 |
| --- | --- |
| Round 3 sneaker GLB | `707cfe6abeb6dff9b9c7e22cf92b0eef23cd3fdc493e580c0584bbc818853d85` |
| Round 2 sneaker GLB | `87098c7a0544bf83fb8c6ed4cc89c866c93af91891a12ef60dc3cbf159e1f608` |
| Master rigged Blender scene | `0339318b375836ab8891e49bda178da7e6f115e012e83385d9f8850949a7bd6f` |
| Motion GLB | `ffccda1ba2a50eb10948853e03d17f0d095cd9b953d644c03c4fb9cb95529410` |


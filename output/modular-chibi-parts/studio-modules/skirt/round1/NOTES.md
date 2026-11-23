# Studio pleated skirt · Round 1

**Technical acceptance passed.** The exported skirt cleared the neutral master in all 14 clips at integer and half frames. The two supplied checker methods reported zero inside vertices and zero garment–body triangle pairs across 1,622 posed samples and one rest sample.

## Deliverables

- [Skinned module](skirt_v1.glb) · [Editable Blender source](skirt_v1.blend) · [Fit script](fit_skirt.py) · [Fitted control mesh](fit_offsets.npz)
- [Six orthographic views](six_view.png) · [Run](run.png) · [Sit idle](sit_idle.png) · [Take item](take_item.png) · [Render manifest](render_manifest.json)
- [Vertex summary](motion_check.txt) · [Vertex samples](motion_check.json) · [Triangle summary](motion_check_tri.txt) · [Triangle samples](motion_check_tri.json)
- [Topology and skin](export_check.json) · [Rest clearance](rest_check.json) · [Khronos validation](gltf_validator.json) · [Blender re-export](blend_replay.json)

| Artifact | Bytes | Triangles |
| --- | ---: | ---: |
| `skirt_v1.glb` | 488,880 | 2,880 |
| `skirt_v1.blend` | 1,271,877 | 2,880 skirt and buckle, plus the editable body reference |

The GLB contains one garment mesh, one skin, and two material primitives. All 65 joint names and inverse bind matrices match the master rig. The cloth uses hips, upper-leg and spine weights, with up to four normalized influences per vertex. The position-welded export has zero boundary edges, non-manifold edges, winding errors and collapsed triangles.

Khronos glTF Validator 2.0.0-dev.3.10 reports **0 errors, 0 warnings** and two informational notices for the preserved source-projection UV set. The two base-colour images are byte-identical to the source JPEGs at **1024 × 1024** and **128 × 128**. The primary UV uses uninterrupted patches from the original atlas to avoid seam streaks after remeshing. The reprojected Studio UV is available as the second UV set. The matte green finish uses a colour factor and smoothed vertex normals on the outer cloth.

GLB SHA-256 `b5e65771b57f3d1c61d237d604abcb702e572831d09921950282573c6a7c0cee`. Reopening the delivered Blender project and re-exporting the module produced the same GLB bytes.

## Fit

The segment silhouettes and base colours identify `tripo_part_1` as the fabric and `tripo_part_6` as the belt. A single Studio import produced a decimated working Blender source. The new loft aligns the source waist to the master waist at roughly 0.426 m and follows the master hip profile around the 0.349 m joint. The hem sits about 0.310 m above the floor, above the 0.209 m knee joint.

The skirt has ten soft pleats. Paired inner and outer rings close both the hem and waistband, and the brass frame is a closed mesh component in the same module. Barycentric body-weight transfer and angular smoothing establish the hip and upper-leg skin. Pose-space contact offsets were mapped back into the rest mesh and baked into the geometry. The indexed surface at `jump` frame 7 cleared after flipping a single quad diagonal. A paired 0.70 mm offset cleared an export-sensitive closest-face switch at `sit_down` frame 26. The final inner wall follows the outer wall’s triangulation at 635 of 640 corresponding quads. The five other quads retain the diagonal required for body clearance.

Hem extensions of 3–14 mm reintroduced contacts. The shorter cut exposes the lower edge of the master’s built-in white briefs. The character, cream shirt, face and shoes in the reference serve as visual context for the wardrobe piece.

## Motion verification

The adapters use the supplied numerical measures at integer frames, half frames and clip endpoints. They reset to neutral for rest and bind the Blender 5 action slot without changing pose-bone rotation modes. The three bank folders include checker-level reports and input hashes.

- Shared clips · [vertex](checkers/shared/motion_check_supplied.json) · [triangles](checkers/shared/motion_check_tri_supplied.json)
- Sit and hold · [vertex](checkers/sit_hold/motion_check_supplied.json) · [triangles](checkers/sit_hold/motion_check_tri_supplied.json)
- Carry · [vertex](checkers/carry/motion_check_supplied.json) · [triangles](checkers/carry/motion_check_tri_supplied.json)

| Clip | Samples | Peak inside vertices | Peak triangle pairs | Min signed mm | Min frame |
| --- | ---: | ---: | ---: | ---: | ---: |
| `walk` | 113 | 0 | 0 | 0.776626 | 26 |
| `run` | 61 | 0 | 0 | 0.731759 | 11 |
| `wave` | 129 | 0 | 0 | 1.758449 | 19 |
| `jump` | 101 | 0 | 0 | 1.187422 | 7 |
| `idle` | 177 | 0 | 0 | 1.737312 | 66 |
| `nod` | 113 | 0 | 0 | 1.798569 | 0 |
| `dance` | 129 | 0 | 0 | 1.759845 | 56 |
| `sit_down` | 73 | 0 | 0 | 0.649486 | 26 |
| `sit_idle` | 181 | 0 | 0 | 1.469309 | 24 |
| `stand_up` | 61 | 0 | 0 | 1.272945 | 22 |
| `hold_item` | 121 | 0 | 0 | 1.740408 | 15 |
| `hold_box` | 121 | 0 | 0 | 1.799855 | 0 |
| `hold_bag` | 121 | 0 | 0 | 1.775479 | 15 |
| `take_item` | 121 | 0 | 0 | 1.745032 | 24 |

The reimported rest mesh has a minimum signed vertex gap of **1.799854 mm**. Across 15,972 vertices, edge midpoints and triangle centres, the maximum Euclidean gap is **29.292174 mm** and the minimum signed gap is **0.812131 mm**.

## Visual review

**Visual acceptance remains open.** The independent reviewer verified the render hashes and inspected each rest view and motion frame. The rest cloth reads more evenly after the matte finish. The short wavy silhouette and brass trim remained intact. White briefs remain visible at the hem and the rear waist.

The `run` capture has angular folds low on the outer skirt. The `sit_idle` capture has a narrow dark crease at the outer hip. The `take_item` capture has continuous visible fabric and small waist gaps. None of these views shows a definite perforation through the cloth. The near-solid fabric colour limits visual verification of texture stretching.

Supplemental self-contact measurements on the reimported GLB cover the depicted poses. They count triangle pairs with no shared vertex within the skirt walls and rims. [Surface review](surface_review.json)

| Pose | Frame | Skirt self-contact pairs |
| --- | ---: | ---: |
| `rest` | 1 | 0 |
| `run` | 11 | 298 |
| `sit_idle` | 24 | 762 |
| `take_item` | 24 | 0 |

The dress-derived profile trials, hem extensions and broad fairing were rejected because they reintroduced skirt–body contacts or reduced the signed clearance below the gate. A final local seated retest reduced some same-skirt contacts while the dark crease remained visible, so the measured candidate above was retained.

## Reproduction

Run these commands from this directory with the guarded Blender 5.1.2 runner. The fit data records the accepted offsets, weights and triangulation. Extraction reuses the reduced source Blender file when it is available.

```sh
sh run_blender.sh fit_skirt.py -- extract
sh run_blender.sh fit_skirt.py -- finish fit_offsets.npz
node validate_skirt.mjs
sh run_blender.sh fit_skirt.py -- audit_rest
sh run_blender.sh fit_skirt.py -- replay
sh run_blender.sh check_skirt.py -- both
sh run_blender.sh render_skirt.py --
sh run_blender.sh check_surface.py --
```

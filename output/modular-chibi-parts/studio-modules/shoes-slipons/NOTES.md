# Blue Studio slip-ons · v1

The shoe pair is an editable [Blender scene](shoes_slipons_v1.blend) and a
mesh-only [GLB module](shoes_slipons_v1.glb). The GLB contains one mesh, two
material primitives, one skin, 65 Mixamo joints and zero animation clips.
Its joint order and inverse binds match the base body export exactly.

| Asset property | Verified result |
| --- | ---: |
| Triangles for the pair | 3,474 |
| Maximum active joint weights | 3 |
| GLB size | 3,765,036 bytes |
| Blender scene size | 3,711,988 bytes |
| Embedded maps | Base color, normal, packed roughness/metalness at 1024 × 1024 each |
| Khronos glTF Validator 2.0.0-dev.3.10 | 0 errors, 0 warnings |

[Asset contract](qa/asset_contract.json) · [Khronos report](qa/validator.json) ·
[Three-quarter preview](qa/preview.png) · [Side preview](qa/rest_side.png)

## Fit and construction

The source GLB imports as one object with two connected shoe shells. In
Blender's Z-up coordinates, their normalized horizontal toe directions are
approximately `(-0.9655, -0.2605, 0)` on the left and `(-0.9557, -0.2944, 0)`
on the right. Each shoe was aligned to `-Y`. The left shoe uses only left
Foot, ToeBase and Leg joints at positive X, and the right shoe uses only the
corresponding right joints. The forward sole averages 88.4% LeftToeBase and
88.3% RightToeBase for exported vertices past the 105 mm forward cutoff.
The toe cap reaches full ToeBase weight. The ball uses a continuous blend,
and the upper and sole share identical welt positions and weights.

The fitted pair retains the original per-corner UVs on 2,974 shoe triangles
and uses the original Tripo material with resized maps. The new recessed
footbed samples the source cavity's UV atlas. The two closed sole slabs have
zero open or inconsistent edges after welding texture seams within each
primitive. Each shoe passes 4,464 upward ray samples around the foot
outline expanded by 3 mm. The full projected sole hull overhang measures
at least 5.26 mm on the left and 6.03 mm on the right. The beveled, planar
tread is narrower than the full slab. Its hull overhang is 2.63 mm on the
left and 3.87 mm on the right. Bare foot length is 192.38 mm. The fitted
soles measure 205.12 mm and 206.16 mm.

The fitter evaluates both feet together across the quaternion clips. It
bakes the worst posed contacts into rest-space geometry, using intersection
witnesses when clear vertices still bound an intersecting triangle. Both
sole and upper positions remain synchronized at the welt. The fit leaves
pose-bone rotation modes intact and assigns the imported Blender 5 action
slots.

[Source-fit measurements](source_fit.json) · [Sole geometry](qa/sole_geometry.json)

## Vertex checker RESULT

| Clip | Maximum vertices inside | Minimum signed distance (mm) |
| --- | ---: | ---: |
| rest | 0 | 2.374 |
| walk | 0 | 2.300 |
| run | 0 | 2.000 |
| wave | 0 | 2.300 |
| jump | 0 | 2.300 |
| idle | 0 | 2.300 |
| nod | 0 | 2.300 |
| dance | 0 | 2.300 |

[Result log](qa/vertex/RESULT.txt) · [Raw JSON](qa/vertex/motion_check.json) ·
[Walk](qa/vertex/walk.png) · [Run](qa/vertex/run.png)

## Triangle checker RESULT

| Clip | Maximum overlapping triangle pairs | Minimum signed distance (mm) |
| --- | ---: | ---: |
| rest | 0 | 2.374 |
| walk | 0 | 2.300 |
| run | 0 | 1.600 |
| wave | 0 | 2.300 |
| jump | 0 | 2.300 |
| idle | 0 | 2.300 |
| nod | 0 | 2.300 |
| dance | 0 | 2.300 |

[Result log](qa/triangle/RESULT.txt) · [Raw JSON](qa/triangle/motion_check_tri.json)

The unchanged checker measurement blocks ran with Cycles CPU for PNG output.
Workbench exited in the supplied environment. Clip distances retain the
supplied checkers' rounding. The additional sweep reimported the same GLB
and checked the full body over **996 samples**, with quarter-frame spacing
in walk and run and half-frame spacing in the other clips. The worst
distance was **1.560 mm**, at run frame 9, with no internal vertices
or body-to-shoe triangle overlap in any sample. [Dense results](qa/dense_check.json)

## Skin pixels and visual review

**0 qualifying skin pixels in all 16 masks.** Four lifted walk poses and
four lifted run poses cover the earlier review frames and the highest
integer-frame lift of each foot in each gait. Every pose is checked from
below and from the lateral side. The paired body-only controls returned
a positive count in every view.

The mask renderer rasterizes Blender's evaluated triangles at 700 × 590.
It compares orthographic depth for the flat green body, the blue sole
and red upper of the inspected shoe. From below it tests the filled
single-shoe silhouette, and from the side it tests the sole and adjoining
holes. A two-pixel exterior band also tests for the target foot's skin
along the sole edge. The above-sole collar and distant green body parts
can be visible beyond the shoe. With the same test, the earlier failed
sneaker asset produced 96,843 qualifying pixels across eight control views.
The raw certification JSON binds every mask PNG to the final export.

An independent reviewer confirmed the rounded toe caps, open ankles, white
bands and the continuity of the sole in walk 19 and run 4 from below and
the side. The reviewed candidate matches the final GLB hash below.

[Pixel counts and camera settings](qa/skin_check.json) ·
[Walk 19 bottom](qa/walk_19_left_below_skin.png) ·
[Walk 19 side](qa/walk_19_left_side_skin.png) ·
[Run 4 bottom](qa/run_04_right_below_skin.png) ·
[Run 4 side](qa/run_04_right_side_skin.png)

## Remaining fit and appearance differences

- The flat tread rests at **Z = −10.0 mm** in the master bind coordinates.
  The bare plantar mesh already reaches Z = 0. A covering sole must pass
  below that plane to keep positive clearance against the current body.
  The recessed footbed is below the skin, with the outer welt up to
  roughly Z = +25.4 mm. A ground-aligned assembly needs a shared vertical
  offset for the character and shoes.
- Rest upper clearance typically falls near the requested range. The
  medians are 8.84 mm left and 8.73 mm right. Local values span about
  2.34–27.83 mm across upper and collar surfaces, including the protruding
  vamp and ankle trim.
- The shoes keep mild rim faceting and small dark slivers inside the
  throat and near the heel welt. Rendered blue is paler than the reference.
  The shoe-only rest BVH reports 147 non-adjacent intersecting pairs
  within shoe components. The sealed sole edge check and every body
  collision and skin-pixel gate pass.

## Rebuild and provenance

From this directory, run the guarded Blender 5.1.2 wrapper and local
checks. The validator uses the existing repository installation.

```sh
work/blender --python fit_shoes.py
work/qa_runner
```

The [deterministic fitter](fit_shoes.py) rebuilt the GLB byte-for-byte
in an isolated output subdirectory. The two supplied checker scripts remain
unchanged and the [render wrapper](work/run_checker.py) substitutes their
renderer only. The local [verification script](work/verify_shoes.py) can
also run the dense, mask and preview checks individually.
[Evidence manifest](qa/evidence_manifest.json)

| File | SHA-256 |
| --- | --- |
| Final GLB | `b9e96178dcf918e6dd89bfce3f933a6b8605773d9bab3e257599b8319f35bd6d` |
| Final BLEND | `8f75b4a5dca45e81a466196335016e1f870690a2e01090139689ec6b75ea2949` |
| Studio source | `d3b42edc3927155aade88d918484298e48f0e070ea3c43db91536c5807d00f15` |
| Master rigged scene | `0339318b375836ab8891e49bda178da7e6f115e012e83385d9f8850949a7bd6f` |
| Motion GLB | `ffccda1ba2a50eb10948853e03d17f0d095cd9b953d644c03c4fb9cb95529410` |

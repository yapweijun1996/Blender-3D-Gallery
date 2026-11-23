# Studio A-line dress, Round 2

The delivered fitting candidate passes the T-pose vertex and triangle collision checks. The seven animated clips still have poke-through.

## Asset

- [Dress GLB](dress_v2.glb) has 2,487,720 bytes, 3,544 triangles and 2,596 exported vertices.
- [Editable Blend](dress_v2.blend) has 3,399,598 bytes. Its master body is available for fitting reference.
- The GLB has 1 skinned garment mesh, 65 master joint names, at most 4 normalized influences per vertex and 0 animations.
- The embedded Tripo textures are 1024 × 1024, 1024 × 1024, 1024 × 1024 px. The material definition and embedded image bytes match Round 1. The source UV layout and material assignment are carried through the bake.
- The local Khronos glTF Validator 2.0.0-dev.3.10 reports 0 errors and 0 warnings.
- GLB SHA-256 `2ea41897d291e6a99a6b071345b42de5e950325ad9af6f6a637991954987d8d1`.
- BLEND SHA-256 `31543375834442b5f0359536d9ed80a3707b1e217657901f36099a88642047e3`.

## Vertex checker RESULT

The supplied checker samples twelve times per clip. Counts are per-frame maxima. Distances are signed and shown in mm.

| Clip | Max inside vertices | Minimum (mm) |
| --- | ---: | ---: |
| rest | 0 | +1.200 |
| walk | 82 | -10.900 |
| run | 111 | -17.800 |
| wave | 39 | -4.600 |
| jump | 61 | -5.500 |
| idle | 40 | -5.100 |
| nod | 39 | -4.400 |
| dance | 31 | -9.600 |

## Triangle checker RESULT

The supplied checker samples every third integer frame. Each pair is one garment triangle overlapping one body triangle. Each signed minimum is a vertex distance.

| Clip | Max triangle pairs | Minimum (mm) |
| --- | ---: | ---: |
| rest | 0 | +1.200 |
| walk | 676 | -13.600 |
| run | 663 | -18.400 |
| wave | 360 | -4.900 |
| jump | 497 | -9.600 |
| idle | 363 | -5.100 |
| nod | 362 | -4.400 |
| dance | 148 | -9.600 |

## Half-frame collision check

Blender reimported the delivered GLB, attached it to the master armature and evaluated 824 poses. Coverage includes rest, every half-frame, both clip endpoints and the supplied checker sample times. The maxima and signed minima can occur at different frames.

| Clip | Poses | Max inside | Max pairs | Vertex min (mm) | Vertex frame | Garment / body zone | Worst inside surface sample (mm) |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- |
| rest | 1 | 0 | 0 | +1.200 | 1 | bodice / Spine1 | — |
| walk | 113 | 96 | 834 | -14.258 | 14.5 | skirt / LeftHand | -13.903 at 13, skirt / LeftHand |
| run | 61 | 136 | 766 | -18.758 | 16.5 | hem / LeftLeg | -16.139 at 9.5, hem / RightLeg |
| wave | 129 | 39 | 360 | -5.112 | 6.5 | skirt / LeftForeArm | -7.887 at 11, bodice / LeftForeArm |
| jump | 101 | 63 | 497 | -10.749 | 36.5 | shoulder and armpit / Spine1 | -8.861 at 10, shoulder and armpit / Spine1 |
| idle | 177 | 41 | 363 | -5.090 | 66 | shoulder and armpit / Spine1 | -7.458 at 66, shoulder and armpit / Spine1 |
| nod | 113 | 39 | 362 | -4.413 | 0 | shoulder and armpit / Spine1 | -7.068 at 0, shoulder and armpit / Spine1 |
| dance | 129 | 31 | 151 | -9.565 | 48 | shoulder and armpit / Spine1 | -7.670 at 48, shoulder and armpit / Spine1 |

Across all half-frame samples the total pair count moved from 204,419 in Round 1 to 271,112 in Round 2. The deepest signed vertex distances moved from -24.306 mm to -18.758 mm. The combined fit score favors lower penetration as well as fewer overlaps.

The [dense report](dense_check.json) records per-clip counts and frames and a garment/body breakdown of the sampled intersection depths. Surface depths sample the triangles around cut segments. Pair counts are direct BVH overlap measurements. The original master has arm and torso self-overlap in several clips, including the left arm and trunk or upper leg at idle frame 66.

## Rest clearance

0 exported vertices exceed 30 mm. Distances are in mm.

| Zone | Vertices | Min | P10 | Median | P90 | P95 | Max |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| all | 2,596 | 1.200 | 5.490 | 14.414 | 24.196 | 25.231 | 28.754 |
| bodice | 508 | 1.200 | 4.920 | 14.352 | 21.103 | 23.032 | 24.673 |
| hem | 554 | 6.812 | 16.102 | 23.202 | 26.312 | 27.130 | 28.430 |
| neck | 398 | 4.583 | 5.229 | 8.870 | 16.470 | 17.896 | 20.595 |
| shoulder and armpit | 184 | 3.565 | 6.014 | 14.056 | 23.965 | 24.490 | 26.364 |
| skirt | 590 | 1.759 | 5.619 | 13.034 | 23.195 | 24.903 | 28.754 |
| sleeve | 362 | 1.200 | 3.879 | 10.977 | 18.618 | 19.712 | 23.087 |

At 14,176 additional triangle centers and edge midpoints, the range is 0.951–28.425 mm. 0 samples fall below 0.5 mm and 0 exceed 30 mm.

The hem opening runs from Z 241.9 to 251.6 mm. The lowest hem point is 33.0 mm above the higher knee joint. Position-welded topology has 4 open boundary loops and 0 edges shared by more than two faces.

## Fitting and reproduction

The fitter reads the Round 1 editable dress, the original master and the supplied motion GLB. It computes a directional bake from nearest-surface contacts over the entire half-frame sweep, with a 2 mm target margin and a 30 mm displacement bound. Triangle-interior witnesses and neighbor-edge checks guide the local offsets. The Laplacian spread retains the selected displacement component before the final shape and rest-clearance guards. Those guards can reduce a required motion correction. Weights in the shoulder, armpit, hip and leg transitions are smoothed and reduced to four normalized influences.

The exploratory seed and subdivision trials revealed that inconsistent weight blends can stretch skirt faces and that extra loops expose skinning errors between old vertex locations. The loft trials split intersecting long edges and added local density around the underarm and inner-thigh junctions. The retained fit uses the best rest-admissible motion score found within the 16 scheduled fit slots.

The selected motion checkpoint was slot 6. Later split candidates contained up to 7,294 triangles and had higher combined collision scores. The delivered mesh retains the 3,544-triangle topology from before those splits. A local rest projection and a final adjustment of the rear hem were applied before reimport and verification. The largest editable vertex displacement from Round 1 was 19.593 mm. The checkpoint recovery was exercised. A fresh all-in-one rebuild hash remains unverified.

Use the guarded Blender 5.1.2 executable and `DYLD_INSERT_LIBRARIES` value supplied with the task from this directory.

```sh
VECLIB_MAXIMUM_THREADS=1 "$BLENDER" -b -noaudio -t 5 --python-exit-code 1 \
  --python fit_dress_r2.py -- build check verify render
```

The checker wrapper runs the supplied measurement and sampling sections and writes separate JSON and text outputs. The headless preview uses Cycles CPU. The fit and render use each Blender action's quaternion channels and assigned slot.

## Renders

The [six-view sheet](six_view.png) shows front, back, left, right, three-quarter, dress only in reading order. Visual self-review shows the round neckline, compact short sleeves and above-knee A-line silhouette. The neckline and hem remain continuous in the sampled rest views. The sleeve ends are more compact than the reference, and the front hem retains a shallow pucker. Walk shows exposure by the cuff and hand. Run shows clear body exposure on the front panel. Jump shows a small exposed spot below the cuff. Wave looks clean from the captured angle and still fails the geometry check.

- [Walk](walk.png), frame 14.5.
- [Run](run.png), frame 16.5.
- [Wave](wave.png), frame 6.5.
- [Jump](jump.png), frame 36.5.

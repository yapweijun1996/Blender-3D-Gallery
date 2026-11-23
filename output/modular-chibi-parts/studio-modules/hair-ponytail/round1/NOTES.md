# High ponytail with fringe · Round 1

**PASS.** The final standalone module has 2,968 triangles and occupies 892,392 bytes (0.851 MiB). Both supplied collision tests found zero penetrations on each of 1,622 half-frame-spaced poses across fourteen clips. The lowest signed vertex clearance was 0.997129 mm in `nod` at frame 17. The independent visual reviewer accepted the six-view sheet and three close-ups for this exact GLB.

[Hair GLB](hair_ponytail_v1.glb) · [Editable fitting scene](hair_ponytail_v1.blend) · [Fit script](fit_hair.py) · [Six views](fit_views_v1.png) · [Fringe](closeup_fringe.png) · [Side](closeup_side.png) · [Nape](closeup_nape.png) · [Machine-readable acceptance](checks/acceptance.json)

## Export and fit

| Measurement | Verified result |
| --- | ---: |
| Exported triangles | 2,968 |
| GLB size | 892,392 bytes |
| Meshes / primitives / materials | 1 / 1 / 1 |
| Editable vertices / exported vertices split at UV seams | 1,484 / 2,050 |
| Embedded Tripo base-colour texture | 1 RGB PNG, 1,024 × 1,024 |
| Master joints / maximum positive influences | 65 / 1 |
| Animation clips in module | 0 |
| Connected components / nonmanifold edges / inconsistent edges / nonadjacent self-intersections | 1 / 0 / 0 / 0 |
| Maximum normal difference at coincident UV-seam positions | 0 |
| Maximum inverse-bind difference from verified same-master side-part module | 0 |
| Maximum reopened editable-to-export position difference | 0.000159 mm |
| Khronos errors / warnings / infos / hints | 0 / 0 / 0 / 0 |

The GLB contains only the hair mesh and its skin. The fitting scene contains the neutral master body and its armature. All hair vertices have normalized unit weight on `mixamorig:Head`. The ponytail, tie and fringe move together. This deliberately preserves the swept silhouette when the head turns and in the sit, hold and carry poses. [Geometry audit](geometry_check.json) · [Khronos glTF Validator 2.0.0-dev.3.10](khronos_validation.json)

### Construction

[Source part inventory](source_parts.json) identifies chestnut `tripo_part_0` (765,610 original triangles, including the tail and tie) and skin-coloured face/ear `tripo_part_2`. A single full Studio import welded coincident positions and decimated the donor hair to 41,999 triangles. The [source working scene](source_working.blend) keeps the donor and face in source coordinates. It is separate from the editable fitted scene.

The frontal eye line and ear positions set the placement, the upper cap fixes the crown, and body rays fit the shell to the neutral master's skull. The radial fitting origins in Blender metres are (0, −0.042, 0.725) on the donor and (0.001, 0, 0.807) on the master. The upper cap, gathered tie and swept tail retain the segmented Studio surface. The lower fringe, ear openings and a continuous turned-under rim replace the irregular cut edge. A curved height profile sets the rear rim between the ears. Additional cross-sections support the lining over the convex scalp. Smooth normals continue across the UV splits.

The outer Studio UV charts retain their horizontal coordinates and are packed into the lower 864 rows of the 1,024 px atlas. The new rim/lining occupies a separate band sampled from the same Studio base colour. The fit replaces black padding and skin-colour spill, reconciles chart tones in surface space, and pads the final UV boundaries by 12 texels. The shipped atlas is a seam-corrected derivative. The working scene retains the original donor UVs and packed base colour.

The [first checked candidate](checks/baseline/fit_views_v1.png) had positive vertex clearance and intersecting triangle interiors. Its largest overlap was 372 pairs in `nod`. Independent review also identified angular fringe ends, a stepped nape and triangle-shaped changes of colour. A constant-material render isolated the triangular colour changes to the donor texture. The revision corrected the chart tones, rounded the ends, curved the nape and redistributed the lining triangles. The [offset bake](offset_bake.json) used rest and two measured extreme samples per clip, all expressed in the head's rest coordinates. It moved 35 vertices by at most 2.0051 mm. Full sweeps then tested the final export. [Baseline extrema](checks/baseline/motion_extremes.json)

## Motion gates

The frame interval is 0.5 and both endpoints are included. Each count is the largest count in that clip. Clearance is the unrounded signed vertex-to-nearest-body-face normal projection, displayed in millimetres. Both the final GLB and the original master are loaded for each checker. The supplied measurement kernels are preserved. The driver selects Blender 5 action slots, expands the loops to integer and half frames, and skips the Workbench preview. The two supplementary banks use their own checker FPS and action binder. All captures use Cycles CPU. The rest measurement is separate from the fourteen clips.

| Clip | Frames | Samples per checker | Inside vertices | Overlap pairs | Min clearance, mm | Frame of minimum |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| walk | 1–57 | 113 | 0 | 0 | 1.7393 | 47 |
| run | 0–30 | 61 | 0 | 0 | 1.7274 | 9 |
| wave | 0–64 | 129 | 0 | 0 | 1.7488 | 33.5 |
| jump | 0–50 | 101 | 0 | 0 | 1.7451 | 9 |
| idle | 0–88 | 177 | 0 | 0 | 1.7484 | 66.5 |
| nod | 0–56 | 113 | 0 | 0 | 0.9971 | 17 |
| dance | 0–64 | 129 | 0 | 0 | 1.7465 | 16 |
| sit_down | 0–36 | 73 | 0 | 0 | 1.7436 | 21 |
| sit_idle | 0–90 | 181 | 0 | 0 | 1.7436 | 23.5 |
| stand_up | 0–30 | 61 | 0 | 0 | 1.7427 | 13 |
| hold_item | 0–60 | 121 | 0 | 0 | 1.7493 | 16.5 |
| hold_box | 0–60 | 121 | 0 | 0 | 1.7495 | 13 |
| hold_bag | 0–60 | 121 | 0 | 0 | 1.7496 | 16 |
| take_item | 0–60 | 121 | 0 | 0 | 1.7489 | 34 |

Rest also returned zero inside vertices and zero overlapping pairs, with a minimum clearance of 1.7499 mm across checker setups. Every tested clip retained more than the required 0.5000 mm signed vertex clearance. The full-precision per-frame JSON and input hashes are in the [shared bank](checks/shared), [sit and hold bank](checks/act) and [carry bank](checks/act2). Each directory contains vertex and triangle summaries, individual frame results, and checker provenance.

## Visual gate

The six tiles show front, left three-quarter, right three-quarter, left profile, rear and right profile in reading order. Each tile is 512 × 512, with a 0.61 m orthographic field. The three feature close-ups are 720 × 720. All use the same neutral AgX, three-light Cycles CPU studio and 12 samples. Only center rays that reach hair before the body count as visible hair. Near-black means Rec. 709 weighted, display-encoded sRGB below 0.12. These counts include real cast and contact shadows.

| View | Visible hair pixels | Near-black pixels | Share |
| --- | ---: | ---: | ---: |
| front | 91,698 | 1,234 | 1.346% |
| three quarter left | 104,061 | 1,541 | 1.481% |
| three quarter right | 73,869 | 35 | 0.047% |
| left | 93,249 | 0 | 0.000% |
| back | 117,922 | 1,298 | 1.101% |
| right | 91,865 | 1,227 | 1.336% |
| **Total** | **572,664** | **5,335** | **0.932%** |

Of the 5,335 near-black pixels, 5,270 fall on the original upper cap or ponytail, 30 on the fitted fringe/front rim, and 35 on the rear rim region. The rear-view nape has zero near-black rim pixels. Most dark pixels trace the natural shadow between the swept tail and cap. The [cyan overlay](checks/near_black_overlay.png) shows the actual counted pixels, including the small temple-area contact shadows. [Six-view counts and image hashes](pixels_v1.json) · [Triangle region attribution](checks/near_black_regions.json)

The independent reviewer passed the high gathered ponytail, chestnut clumps, short lobed fringe, clear eyes, scalp contact at both temples, and smoothly curved nape. The former triangular colour patches, pale bang streak and stepped rear edge cleared. The reviewer saw a small opening between the lifted tail and the crown at the tie, plus a thin contact shadow behind the ear. Neither opens the hair-to-scalp contact line. A short flat segment on the centre-right fringe tip, mildly blunt temple tips, slight silhouette facets and the donor's stronger twist remain visible at close range. Only a front reference was supplied. The nape was judged against the requested curvature. [Independent visual review](checks/visual_review.json)

A second frontal check cast rays on a 0.5 mm grid over both eye windows using the master's dark iris/lid base-colour marks. The fringe covered 0 of 15,308 samples on the viewer's left and 0 of 15,604 on the right. The smallest sampled vertical margins were 6.5 mm and 18.0 mm. These are front-projection eye margins. [Eye check](eyes_check.json)

## Rebuild and verify

Run the following sequentially from this directory, using the project-local Node environment and guarded Blender 5.1.2. The launcher pins Blender to two threads and creates a local scratch directory. The first command is only needed to reconstruct the included source working scene. The fit regenerates the pose cache locally from the measured baseline extrema.

```sh
node run.cjs prepare_source.py
node run.cjs fit_hair.py
node run.cjs audit.py
node validate.cjs
node run.cjs check_motion.py
node run.cjs render_views.py
node run.cjs inspect_shadows.py
node run.cjs check_eyes.py
node verify_delivery.cjs
```

A different export hash requires a fresh visual review and matching review record for the final verification command. The SHA-256 for this GLB is `489e7ba6e76d83b20e7645c3ec3a030df8b05338d6d1a4a7471ed1e8fedf1221`. Source, master, reference and editable-scene hashes are recorded in [acceptance.json](checks/acceptance.json).

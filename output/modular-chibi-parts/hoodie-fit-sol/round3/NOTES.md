# Hoodie fit, round 3

The exported hoodie is clear in the T-pose. The animation vertex and triangle zero-contact criteria remain open.

## Artifacts

The model files, the Blender fitter, both supplied-checker results, the dense check and the PNGs are in this directory.

- GLB 1,304,484 bytes and BLEND 2,315,429 bytes.
- One skinned garment mesh, 7,000 triangles, 4,357 exported vertices, 65 joints and at most 4 normalized influences per vertex.
- One embedded 1024 × 1024 PNG, with the same image bytes as round 2. The export contains zero animations.
- Khronos glTF Validator 2.0.0-dev.3.10 reported 0 errors and 0 warnings.
- GLB SHA-256 `29cc22b68ffb16f5c91ed550ab23851f37c9841fbcd211a96d35450bb342868e`.
- BLEND SHA-256 `b49b9cd8060a84e9d314aafd1625999ed27ae1f7e60665c6cf33154af83b1401`.

## Supplied checker RESULT tables

The vertex checker samples twelve times per clip. The triangle checker samples every third integer frame. Each count is the maximum in one sample. Each minimum is the smallest signed vertex distance across the samples. The checker scripts retain their original rounding for clip distances.

### Vertex checker

| Clip | Inside vertices | Min vertex clearance (mm) |
| --- | ---: | ---: |
| rest | 0 | +0.430 |
| walk | 179 | -18.700 |
| run | 115 | -12.600 |
| wave | 85 | -7.300 |
| jump | 104 | -10.500 |
| idle | 96 | -7.300 |
| nod | 86 | -7.800 |
| dance | 54 | -7.200 |

### Triangle checker

| Clip | Overlapping pairs | Min vertex clearance (mm) |
| --- | ---: | ---: |
| rest | 0 | +0.430 |
| walk | 1,000 | -15.600 |
| run | 684 | -11.400 |
| wave | 560 | -7.300 |
| jump | 576 | -11.200 |
| idle | 576 | -7.300 |
| nod | 564 | -7.700 |
| dance | 206 | -7.200 |

## Half-frame RESULT

The final GLB was reimported into the master scene and evaluated at 824 poses including T-pose, integer frames, half frames, both clip endpoints and the supplied checker times. The count and distance columns can reach their extremes in different poses.

| Clip | Poses | Inside vertices | Deepest vertex (mm) | Vertex frame | Triangle pairs | Pair frame | Round 2 pairs |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| rest | 1 | 0 | +0.430 | 1 | 0 | 1 | 0 |
| walk | 113 | 206 | -19.061 | 42 | 1,025 | 35 | 1,629 |
| run | 61 | 210 | -17.539 | 23 | 829 | 8 | 1,337 |
| wave | 129 | 91 | -7.323 | 54.5 | 560 | 0 | 866 |
| jump | 101 | 106 | -11.240 | 39 | 576 | 9 | 990 |
| idle | 177 | 97 | -7.306 | 82.5 | 576 | 78 | 878 |
| nod | 113 | 86 | -7.892 | 23.5 | 565 | 31 | 876 |
| dance | 129 | 54 | -7.227 | 40 | 206 | 48 | 603 |

Across all 824 poses, the sum of triangle-pair counts fell from 707,793 in round 2 to 379,906 in round 3. The deepest signed vertex distance regressed from −10.621 mm to −19.061 mm on the same half-frame sweep. The chosen bake is a tradeoff between these results.

## Rest clearance

Clearances use nearest oriented body triangles on the reimported GLB. The torso panels use the 20 mm limit. The shoulders, armpits, sleeves and hem use the 30 mm allowance. The cuff reach is pinned near the original wrist openings. Collar and hood are reported separately.

| Region | Vertices | Min (mm) | P10 (mm) | Median (mm) | P90 (mm) | P95 (mm) | Max (mm) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Torso overall | 2,161 | 0.607 | 3.815 | 8.431 | 15.609 | 18.077 | 21.964 |
| Torso panels | 1,117 | 0.607 | 4.282 | 9.113 | 16.922 | 19.332 | 19.913 |
| Hem | 566 | 2.283 | 4.800 | 9.747 | 15.449 | 16.767 | 20.785 |
| Shoulder and armpit | 478 | 1.344 | 2.743 | 5.546 | 10.770 | 11.950 | 21.964 |
| Sleeves | 656 | 0.430 | 2.108 | 4.869 | 17.044 | 19.897 | 29.936 |
| Cuffs | 208 | 0.829 | 1.561 | 4.477 | 13.204 | 14.101 | 18.815 |
| Front collar | 324 | 5.866 | 12.264 | 22.712 | 27.529 | 28.697 | 32.111 |
| Hood | 1,008 | 4.500 | 9.996 | 21.642 | 51.285 | 62.710 | 85.865 |

The cuff extrema are X = +265.902 mm on the left and X = -262.958 mm on the right. The corresponding rest wrist joints are at X = +270.898 mm and −270.421 mm. The cuffs end 5.0 mm and 7.5 mm short of those joints along X. The T-pose renders show clear wrist openings and visible creasing at the sleeve roots and hem.

## Residual contacts

The JSON lists every failing half-frame, the exact checker count, and the deepest sampled signed distance. Interior depths sample a barycentric grid with 10 subdivisions plus the triangle intersection witnesses. The sample depth estimates the largest penetration over each surface patch. The BVH pair counts are exact for each measured pose.

| Clip | Overlapping frames | Pairs at deepest frame | Deepest sampled interior (mm) | Frame |
| --- | ---: | ---: | ---: | ---: |
| walk | 113 | 587 | -16.479 | 46.5 |
| run | 61 | 650 | -12.608 | 5 |
| wave | 129 | 490 | -7.771 | 14.5 |
| jump | 65 | 576 | -12.873 | 9 |
| idle | 177 | 574 | -7.967 | 66 |
| nod | 113 | 560 | -7.892 | 23.5 |
| dance | 115 | 204 | -7.747 | 45 |

Residuals extend beyond the armpit and inner elbow. See the per-frame garment region and dominant body-joint breakdown in [dense_check.json](dense_check.json). The original master motion also has arm-to-body intersections. For example, at idle 0 the left arm and the hips/leg faces have 42 body-to-body triangle pairs, and at run 8 the right arm and the hips/leg faces have 108. The fit uses the original master and quaternion clips.

## Method and reproduction

Round 2 contains isolated off-branch weights that let vertices clear while stretched triangles still cross the body. An idle cuff edge with a Hips endpoint and a ForeArm endpoint measured about 209 mm posed from a 20 mm rest edge. This fit rebinds the panels, shoulders and sleeves against the master surface, smooths the affected joint transitions, and splits 997 edges prioritized by intersecting faces and edge length. The pre-existing UVs and embedded texture are retained.

The solver projects the worst vertex and triangle-interior constraints over all half-frame poses with a 2.05 mm target margin. Neighborhood smoothing keeps the required displacement component before candidate limits and the rest mesh guard. Skin weights are smoothed and reduced to four after geometry changes. Rest shape guards and candidate rejection can leave unmet margin and contact constraints.

The final fitting search used 12 update slots and selected iteration 11 by the joint dense score. Both checker gates remain unmet for the clips. The search resumed from the saved best topology and weights after the fifth update. The supplied build command runs from round 2 through the full search. Byte-for-byte reproduction from a fresh build remains unverified.

Use the supplied guarded Blender 5.1.2 binary and DYLD setting from this directory.

```sh
"$BLENDER" -b -noaudio --python-exit-code 1 --python fit_hoodie_round3.py
"$BLENDER" -b -noaudio --python-exit-code 1 --python fit_hoodie_round3.py -- --checkers
"$BLENDER" -b -noaudio --python-exit-code 1 --python fit_hoodie_round3.py -- --verify
"$BLENDER" -b -noaudio --python-exit-code 1 --python fit_hoodie_round3.py -- --renders
```

The fitter reuses the earlier fit scripts and the round 2 BLEND in their gallery locations. The checker wrapper executes both supplied measurement paths and uses separate report filenames. It bypasses Workbench rendering in headless Blender. The PNGs use Cycles CPU on the reimported GLB.

Motion PNG frames show the highest measured overlap count for each clip. The rest PNGs show the T-pose from the front, back and side, plus the hoodie on its own. The walk and run renders show remaining bunched cloth near the inner sleeve and torso.

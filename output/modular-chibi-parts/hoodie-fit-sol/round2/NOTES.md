# Hoodie fit, round 2

The delivered hoodie passes the T-pose vertex and triangle checks and the 20 mm rest torso limit. All seven motion clips still have penetrations after six fitting iterations. The largest dense penetration is 5.549 mm, down from 17.077 mm in round 1.

## RESULT

Counts are the largest number of inside vertices in any sampled frame. The supplied checker samples 12 frames per clip. The dense check reimports the exported GLB onto the master armature and measures 416 poses, including rest, every integer frame through both clip endpoints, and the checker's sample times. The two figures in each result cell are the maximum count and minimum signed distance in mm. Each row needs zero inside vertices and at least +0.500 mm clearance.

| Clip | Round 1 checker count | Round 2 checker count / min (mm) | Round 1 dense count | Round 2 dense count / min (mm) | Dense poses |
| --- | ---: | ---: | ---: | ---: | ---: |
| rest | 0 | 0 / +0.882 | 0 | 0 / +0.882 | 1 |
| walk | 100 | 20 / -4.300 | 104 | 22 / -5.549 | 57 |
| run | 54 | 32 / -2.400 | 141 | 32 / -4.247 | 31 |
| wave | 18 | 7 / -2.300 | 20 | 7 / -2.269 | 65 |
| jump | 35 | 13 / -4.700 | 55 | 16 / -4.697 | 51 |
| idle | 3 | 2 / -0.500 | 3 | 2 / -0.546 | 89 |
| nod | 3 | 1 / -1.000 | 4 | 1 / -1.185 | 57 |
| dance | 21 | 15 / -0.900 | 21 | 16 / -0.989 | 65 |

## Rest clearance

The torso covers the panels, hem, shoulders and armpits. The lower hood and front collar are reported separately from the torso, as are sleeves and cuffs. All measurements use signed nearest-body distance on the reimported GLB. The rest body and garment BVHs report zero intersecting face pairs.

| Region | Vertices | Min (mm) | P10 (mm) | Median (mm) | P90 (mm) | P95 (mm) | Max (mm) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Torso overall | 1,481 | 0.882 | 4.134 | 9.008 | 15.347 | 18.236 | 19.734 |
| Torso panels | 892 | 1.001 | 4.748 | 9.944 | 17.405 | 19.350 | 19.734 |
| Hem | 309 | 1.257 | 4.458 | 9.821 | 12.490 | 13.385 | 15.042 |
| Shoulder and armpit | 280 | 0.882 | 2.215 | 6.445 | 10.010 | 10.908 | 18.081 |
| Sleeves | 353 | 1.043 | 2.474 | 7.857 | 18.880 | 20.994 | 26.590 |
| Cuffs | 148 | 1.068 | 2.783 | 5.711 | 13.330 | 14.011 | 15.167 |
| Front collar | 315 | 6.798 | 13.180 | 22.949 | 27.551 | 28.798 | 32.111 |
| Hood | 982 | 4.500 | 9.888 | 21.660 | 51.904 | 62.789 | 85.865 |

The rest renders show the fitted torso, rear hood and open cuffs. The garment-only view still shows two dark creases in the front hem and faceting on the sleeves. The supplied run render shows small folds projecting at the sleeve and hem during the simulated arm swing.

## Remaining penetrations by region

The body zone is the dominant skin joint on the nearest body face. Each row gives a zone pair's most negative signed distance and the frame where it occurred. The dense JSON also records zone pairs with positive clearance below the +0.500 mm target.

| Clip | Garment region | Body zone | Frame | Minimum signed distance (mm) |
| --- | --- | --- | ---: | ---: |
| walk | Torso panels | `LeftForeArm` | 39 | -5.549 |
| walk | Hem | `LeftForeArm` | 40 | -5.353 |
| walk | Cuffs | `LeftUpLeg` | 26 | -5.247 |
| walk | Hem | `RightForeArm` | 5 | -4.011 |
| walk | Torso panels | `LeftArm` | 13 | -3.932 |
| walk | Sleeves | `Spine1` | 54 | -3.685 |
| walk | Hem | `LeftUpLeg` | 35 | -1.766 |
| walk | Torso panels | `RightForeArm` | 39 | -1.752 |
| walk | Torso panels | `LeftUpLeg` | 23 | -1.722 |
| walk | Torso panels | `RightArm` | 1 | -1.578 |
| walk | Sleeves | `LeftUpLeg` | 49 | -1.263 |
| walk | Torso panels | `Spine1` | 22 | -1.209 |
| walk | Shoulder and armpit | `LeftArm` | 40 | -1.118 |
| walk | Shoulder and armpit | `Spine1` | 16 | -0.666 |
| walk | Sleeves | `Hips` | 31 | -0.604 |
| walk | Shoulder and armpit | `RightArm` | 23 | -0.500 |
| walk | Sleeves | `RightUpLeg` | 3 | -0.497 |
| walk | Torso panels | `Hips` | 41 | -0.118 |
| run | Cuffs | `LeftUpLeg` | 29 | -4.247 |
| run | Sleeves | `Spine1` | 23 | -4.140 |
| run | Hem | `LeftUpLeg` | 8 | -3.042 |
| run | Torso panels | `LeftForeArm` | 16 | -2.570 |
| run | Hem | `Hips` | 18 | -2.537 |
| run | Hem | `RightUpLeg` | 0 | -2.450 |
| run | Hem | `LeftForeArm` | 29 | -2.413 |
| run | Torso panels | `Spine1` | 24 | -2.239 |
| run | Shoulder and armpit | `LeftArm` | 17 | -1.434 |
| run | Hem | `RightHand` | 6 | -1.134 |
| run | Torso panels | `RightForeArm` | 8 | -0.971 |
| run | Torso panels | `Hips` | 6 | -0.969 |
| run | Shoulder and armpit | `Spine1` | 24 | -0.908 |
| run | Shoulder and armpit | `RightArm` | 7 | -0.690 |
| run | Hem | `LeftHandThumb1` | 29 | -0.566 |
| run | Torso panels | `RightHandIndex1` | 4 | -0.499 |
| run | Hem | `RightHandMiddle1` | 5 | -0.463 |
| run | Torso panels | `LeftUpLeg` | 9 | -0.433 |
| run | Torso panels | `RightArm` | 16 | -0.359 |
| run | Sleeves | `RightArm` | 5 | -0.275 |
| run | Shoulder and armpit | `RightShoulder` | 5 | -0.135 |
| run | Hem | `LeftHand` | 29 | -0.076 |
| run | Torso panels | `LeftArm` | 28 | -0.044 |
| run | Sleeves | `LeftUpLeg` | 23 | -0.040 |
| run | Torso panels | `RightShoulder` | 19 | -0.013 |
| wave | Cuffs | `LeftUpLeg` | 19 | -2.269 |
| wave | Hem | `LeftForeArm` | 50 | -1.353 |
| wave | Torso panels | `RightArm` | 58 | -0.383 |
| wave | Shoulder and armpit | `RightShoulder` | 59 | -0.270 |
| wave | Sleeves | `RightForeArm` | 19 | -0.264 |
| wave | Sleeves | `RightArm` | 35 | -0.204 |
| wave | Shoulder and armpit | `RightArm` | 3 | -0.090 |
| jump | Cuffs | `LeftUpLeg` | 4 | -4.697 |
| jump | Sleeves | `Spine1` | 10 | -3.264 |
| jump | Torso panels | `LeftForeArm` | 36 | -3.120 |
| jump | Hem | `LeftForeArm` | 42 | -2.819 |
| jump | Sleeves | `LeftUpLeg` | 5 | -2.452 |
| jump | Shoulder and armpit | `LeftArm` | 11 | -0.839 |
| jump | Shoulder and armpit | `Spine1` | 34 | -0.682 |
| jump | Torso panels | `LeftArm` | 5 | -0.475 |
| jump | Shoulder and armpit | `RightShoulder` | 39 | -0.432 |
| jump | Torso panels | `RightArm` | 36 | -0.427 |
| jump | Shoulder and armpit | `RightArm` | 35 | -0.323 |
| idle | Shoulder and armpit | `RightShoulder` | 29 | -0.546 |
| idle | Hem | `LeftForeArm` | 22 | -0.434 |
| nod | Hem | `LeftForeArm` | 15 | -1.185 |
| dance | Sleeves | `Spine1` | 40 | -0.989 |
| dance | Shoulder and armpit | `LeftArm` | 38 | -0.927 |
| dance | Shoulder and armpit | `Spine1` | 56 | -0.774 |
| dance | Torso panels | `RightArm` | 8 | -0.404 |
| dance | Shoulder and armpit | `RightArm` | 20 | -0.250 |

## Build and validation

The script starts from the editable round 1 hoodie and uses its mesh connectivity, UVs and packed texture. Across six iterations it measures every garment vertex on all dense poses, projects each deficit into rest space, clamps the required offset to 20 mm, and applies three neighborhood Laplacian passes with the original requirement as a floor. Candidate changes are tested against dense poses and rejected if they flip, pinch or intersect the rest body. Persistent contacts also use local inverse-skinned directions and skin-weight adjustments. A final bounded neighborhood pass tests local loosening and takes in the upper torso. All measured poses use the supplied quaternion tracks and the master bone rotation modes.

The GLB contains 1 garment mesh, 5,022 triangles, 3,279 exported vertices, 65 matching joints and at most 4 influences per vertex. It contains one embedded 1024 × 1024 PNG and zero animations. The GLB is 1,236,560 bytes, and the editable BLEND is 2,196,112 bytes. The local Khronos validator 2.0.0-dev.3.10 reported 0 errors and 0 warnings.

The supplied checker file is unchanged. Headless Workbench aborted with exit 134, so the runner used Cycles CPU at 16 samples for the checker's four 500 × 500 PNGs. The rest views use Cycles CPU at 12 samples and 900 × 560. The supplied sampling, measurements, camera and image frames were preserved. Motion PNGs show one pose per rendered clip. Visual review was performed on the captured images.

Run from this directory using the supplied guarded Blender 5.1.2 binary and `DYLD_INSERT_LIBRARIES` setting.

```sh
"$BLENDER" -b -noaudio --python-exit-code 1 --python fit_hoodie_round2.py
"$BLENDER" -b -noaudio --python-exit-code 1 --python fit_hoodie_round2.py -- --checker
"$BLENDER" -b -noaudio --python-exit-code 1 --python fit_hoodie_round2.py -- --renders
```

`--verify` independently remeasures the existing v2 GLB. `--baseline` remeasures the round 1 GLB. The build uses fixed seeds, ordered samples and stable sorting. A second complete byte-for-byte build comparison remains unmeasured.

## Evidence

Final GLB SHA-256 `b7a1de41be3037702509ba540ac200f75647132e70f5f5b3e4ec3920be8640b5`

| Artifact | SHA-256 |
| --- | --- |
| [`top_hoodie_v2.blend`](top_hoodie_v2.blend) | `424dea35d5adb2a3c3d2ae3ae71c0c52e964b8cac35ae2f0745c95c0fb77a2aa` |
| [`fit_hoodie_round2.py`](fit_hoodie_round2.py) | `31e160e45877578f2a986129fbcebb97ba29b5e23aede3473610837eab858f39` |
| [`motion_check.py`](motion_check.py) | `5e5b269858431688f2f853a38230227362cb88faf9aa2f588e514840486e96d8` |
| [`motion_check.json`](motion_check.json) | `0de725fd8c39134730bcd1bc0d9073d5568a8732665d2212e21f7c8850e98377` |
| [`motion_check.txt`](motion_check.txt) | `a6459f5c677c1af45ade4d6904b1a8c0a6905886b95d093a7685c6dc65af7c15` |
| [`dense_check.json`](dense_check.json) | `f71b567a9fef1caa99c818b0f35bb745acd433fd6adce518461a9ae720612774` |
| [`gltf_validator.json`](gltf_validator.json) | `1685d4430275784fea85c4b899189c0222ba028523cc5f702f52a05c0c6dfb38` |
| [`walk.png`](walk.png) | `66afeba40d1d1dafc79f50d1b0022930483fa4e1fecf3a1932a48a9ea50b38a1` |
| [`run.png`](run.png) | `c96b9a28797f0d2a03d511726a5777c449d74df878e9754756b8aa89d9112006` |
| [`wave.png`](wave.png) | `3e75ff6aa6bdf602ed53faaae0c9bc9206982a2d696c4289065bce00b3a643a0` |
| [`jump.png`](jump.png) | `94d6dcca1891c7195bb36adf09e0fba8c5c517c3374941f6fc8f2196a99ad251` |
| [`rest_front.png`](rest_front.png) | `2f6fd7bbc9e13328343b00861b31a4ac055fe72a8af9a9ed885eaad489dc832a` |
| [`rest_back.png`](rest_back.png) | `87b3f3d100627e3d3c1d525e9599a9b2afd75816e766139985ba53f0f89852a8` |
| [`rest_hoodie.png`](rest_hoodie.png) | `142eea6ef493758ed8b9e55ab750bfc4a2204195b58f426680c9741e1ac80f6b` |

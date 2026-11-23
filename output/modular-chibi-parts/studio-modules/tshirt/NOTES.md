# Tripo Studio gamepad T-shirt

**REWORK.** The fitted T-shirt passes both rest collision gates. Seven motion clips retain body contacts. The deepest half-frame vertex penetration is 14.424 mm in `walk`. The GLB is a review candidate.

The GLB has **3,903 triangles**, **3,193,296 bytes**, one skinned garment mesh, 65 matching joints, and at most four nonzero influences. The BLEND is **4,031,204 bytes**. Local Khronos glTF Validator 2.0.0-dev.3.10 found **0 errors and 0 warnings**.

The left and right cuff opening centers lie at 41.2% and 44.4% of the bone-defined upper arm. The hem opening spans z = 0.3948 to 0.4018. The welded mesh has four perimeter openings and 0 edges shared by more than two faces.

## Vertex checker RESULT

| Clip | Max inside vertices | Minimum signed distance (mm) |
| --- | ---: | ---: |
| rest | 0 | +2.100 |
| walk | 149 | -12.200 |
| run | 94 | -8.700 |
| wave | 85 | -9.000 |
| jump | 116 | -10.100 |
| idle | 115 | -8.500 |
| nod | 90 | -8.900 |
| dance | 46 | -4.800 |

## Triangle-overlap checker RESULT

| Clip | Max overlap pairs | Minimum signed distance (mm) |
| --- | ---: | ---: |
| rest | 0 | +2.100 |
| walk | 640 | -14.400 |
| run | 493 | -12.800 |
| wave | 359 | -9.200 |
| jump | 388 | -10.400 |
| idle | 370 | -8.500 |
| nod | 361 | -8.900 |
| dance | 140 | -4.800 |

The two supplied checkers select different frame subsets. Their motion distances are rounded to 0.1 mm by the checker. Both use the +0.500 mm clearance threshold.

## Half-frame verification

[dense_check.json](dense_check.json) measures the reimported GLB in 824 samples including T-pose, half-frame intervals and clip endpoints. Triangle depths are sampled witnesses on intersecting faces. Their zone pairs name the garment area and the dominant bone of the nearest body face.

| Clip | Samples | Max inside vertices | Max overlap pairs | Deepest vertex (frame, zone, mm) | Deepest triangle witness (frame, zone, mm) |
| --- | ---: | ---: | ---: | --- | --- |
| rest | 1 | 0 | 0 | — | — |
| walk | 113 | 168 | 640 | 52.5, hem / LeftForeArm, -14.424 | 45.5, hem / LeftForeArm, -14.791 |
| run | 61 | 167 | 525 | 24, front panel / LeftForeArm, -12.843 | 9, front panel / LeftArm, -11.065 |
| wave | 129 | 89 | 359 | 9, back panel / LeftForeArm, -9.171 | 19, back panel / LeftForeArm, -9.400 |
| jump | 101 | 118 | 388 | 9, front panel / LeftForeArm, -10.378 | 7, front panel / LeftForeArm, -9.270 |
| idle | 177 | 115 | 370 | 66, back panel / LeftForeArm, -8.492 | 66, back panel / LeftForeArm, -8.492 |
| nod | 113 | 91 | 366 | 17, back panel / LeftForeArm, -8.892 | 17, back panel / LeftForeArm, -8.892 |
| dance | 129 | 46 | 141 | 48, front panel / LeftForeArm, -4.797 | 48, back panel / LeftArm, -5.302 |

## Rest clearance in mm

| Region | Min | P10 | Median | P90 | P95 | Max |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| overall | 2.000 | 4.579 | 9.376 | 20.973 | 20.999 | 27.586 |
| back panel | 3.008 | 5.465 | 10.833 | 15.735 | 18.777 | 20.514 |
| collar | 4.766 | 5.211 | 10.555 | 20.163 | 20.964 | 21.028 |
| front panel | 2.807 | 9.182 | 20.581 | 21.000 | 21.000 | 27.586 |
| hem | 2.000 | 3.536 | 7.580 | 13.960 | 16.542 | 20.810 |
| shoulder / armpit | 2.000 | 3.912 | 6.996 | 11.682 | 13.513 | 20.923 |
| sleeve / cuff | 2.100 | 3.548 | 6.693 | 9.429 | 11.067 | 17.770 |

## Iteration selection

The 12-pass build retained pass 7 for its combined collision score and clean rest state. The pass 2 contact scan selected 75 long edges for local subdivision. Relative to the fitted starting shape, pass 7 reduced the aggregate inside-vertex count and increased the aggregate triangle-pair count slightly. Later passes reduced inside vertices further but reintroduced rest triangle intersections. The supplied checks and half-frame report assess the final export after restoring the logo contour and smoothing the front hem.

A separate Blender contact test on the ungarmented master found 21 left and 24 right distal-arm/torso overlap pairs at walk frame 35, one pair at run frame 8, and four at wave, idle and nod frame 0. The body self-contact is a contributing condition around the side panels and sleeves. The final report records the remaining garment contacts for every clip.

## Visual review

Both the author and an independent reviewer inspected the six rest views and four motion frames. The reviewer matched all ten image digests to the exact GLB. The rest views show the purple collar, short cuffs and readable gamepad with continuous neck and hem coverage. Mild faceted wrinkles remain along the front band and sides.

The motion visual gate fails. Walk frame 23 exposes a tan wedge on the viewer-left lower flank above the hem, behind the forward arm. Run frame 12 shows hem bunching, with the hands occluding part of the chest and neck. The visible collar and hem remain continuous in wave frame 25 and jump frame 20. These visual observations cover the four recorded motion frames.

- Rest views [front](renders/rest_front.png), [back](renders/rest_back.png), [left](renders/rest_left.png), [right](renders/rest_right.png), [front three-quarter](renders/rest_front_three_quarter.png), [back three-quarter](renders/rest_back_three_quarter.png)
- Motion frames [walk 23](renders/walk.png), [run 12](renders/run.png), [wave 25](renders/wave.png), [jump 20](renders/jump.png)

## Inputs and build

The source GLB is Tripo Studio Best Quality with quad retopology, exported as 5,606 triangles. Its gamepad faces Blender −Y after import, matching the master body. The build welds UV duplicates geometrically, keeps the visible outer shell, opens the collar, two cuffs and hem, and repairs small unintended holes. The source UV chart and three Tripo PBR maps are retained. Each map is resampled to 1024 × 1024.

The garment uses barycentric nearest-body face weights with local smoothing at the shoulders, underarms and hips, normalized to at most four influences. The seven input actions use the master armature's existing quaternion modes and the imported Blender 5 action slots. Fitting samples both endpoints of every clip and every intervening half frame. Both signed vertices and intersecting triangle witnesses drive a 2 mm clearance target. The rest shape is capped at 30 mm. Opposing contact directions use local position and weight adjustments. The final front-band polish smooths pinched geometry along the existing UVs.

The editable BLEND includes the reference body used for fitting. The GLB carries one garment mesh, its skin and bind transforms, and its material. The master and motion sources were used read-only. The render scene uses Cycles CPU after the supplied Workbench path exited with code 134. Only the render calls and colliding JSON output filenames were adapted in the checker runner. Their frame sampling and measurements were preserved. The exact render frames and PNG hashes are in [render_info.json](render_info.json).

Run from the T-shirt directory with the provided guarded Blender 5.1.2, the matching `DYLD_INSERT_LIBRARIES` setting, and the existing `work/motion_check*.py` files.

```sh
"$BLENDER" -b -noaudio -t 2 --python-exit-code 1 --python fit_tshirt.py
"$BLENDER" -b -noaudio -t 4 --python-exit-code 1 --python fit_tshirt.py -- --checkers
"$BLENDER" -b -noaudio -t 4 --python-exit-code 1 --python fit_tshirt.py -- --verify
"$BLENDER" -b -noaudio -t 6 --python-exit-code 1 --python fit_tshirt.py -- --renders
```

`--output <relative directory>` can isolate reproduction outputs within the module. The build orders the source vertices and faces explicitly and uses fixed fit samples, edge priorities and contacts. A repeat through the selected pass 7 reproduced the fitted GLB byte-for-byte before polishing. Rebuilding the source reference and then repeating the logo and hem polish with two Blender threads reproduced the delivered GLB byte-for-byte. The same finishing replay with four Blender threads changed some vertex coordinates by up to 0.198 mm per axis. Use the documented thread count for the byte comparison.

## Input SHA-256

| Input | SHA-256 |
| --- | --- |
| `source_studio_retopo.glb` | `04c8eda2b71811e6abdd02066df8103dde88b2accfb7fd656cfc4744aa90d933` |
| `GJH_Chibi_Master_rigged.blend` | `0339318b375836ab8891e49bda178da7e6f115e012e83385d9f8850949a7bd6f` |
| `motion.glb` | `ffccda1ba2a50eb10948853e03d17f0d095cd9b953d644c03c4fb9cb95529410` |
| `tpose-top-02-tshirt-gamepad.png` | `c6f5e9b1caf1eb0142a9ec1beb41855e8bf70619f5f7c04e0067ef120c09ed82` |

## Deliverables and evidence

- [Editable scene](tshirt_v1.blend), [skinned GLB](tshirt_v1.glb), [build script](fit_tshirt.py)
- [Vertex checker TXT](motion_check.txt), [vertex checker JSON](motion_check.json), [triangle checker TXT](motion_check_tri.txt), [triangle checker JSON](motion_check_tri.json)
- [GLB structure and opening measurements](export_check.json), [Khronos result](gltf_validation.json), [fit iteration history](fit_history.json), [render manifest](render_info.json)
- Final GLB SHA-256 `b3720ea4780f0cc98e28185749cb6f0284a7132481cf0a7e8eb419183e8b5034`

# Purple star high-top shoes

[Editable shoe and fitting scene](shoes_hightop_v1.blend) · [Skinned module](shoes_hightop_v1.glb) · [Blender builder](fit_shoes.py) · [Pair preview](png/shoes_preview.png) · [Opposite view](png/shoes_opposite.png) · [Fitted rest pose](png/fitted_rest.png)

## Fit and exported asset

The Tripo GLB imports as one mesh containing two disconnected shoe shells. The shoes already face Blender −Y (glTF +Z). The shell at +X was fitted to the character's left foot and the shell at −X to the right. The original exterior construction, Tripo material, and per-corner UVs were carried forward. The shallow stock shoe pocket was replaced with a fitted lining and closed footbed. The source had 3,083 triangles after import, and the new pair retains 2,951 source faces.

Main body and sole weights use the same-side Foot and ToeBase bones, with Leg at the heel and collar. Forefoot weights blend through the ball. Local shifts were baked into the rest mesh using posed vertex and triangle contact witnesses. The full-body pass addressed the opposite foot at the left medial tread in walk and the same-side thigh near the right collar in run. The rear collar tapers under the deep knee bend while the tongue reaches Z ≈ 0.146 m. The saved Blender scene includes the master body, armature, and seven quaternion actions for inspection. The exported GLB has one skinned shoe mesh, 65 joints, and zero embedded animations. The joint order and inverse-bind matrix bytes match the round-three sneaker.

| Export property | Result |
| --- | ---: |
| Triangles, left + right | 3,383 (1,685 + 1,698) |
| Nonzero joint influences per vertex | ≤3 |
| Base color, normal, and roughness/metalness textures | 1,024 × 1,024 each |
| GLB bytes | 4,602,568 |
| Blender scene bytes | 5,843,781 |
| Khronos validator errors / warnings | 0 / 0 |

Both sole regions have zero open or nonmanifold edges. A vertical ray test of the projected body footprint plus 3 mm made 1,257 samples per shoe and found zero missed samples. The median inner upper clearance is 5.61 mm left and 5.55 mm right. The 5th to 95th percentile ranges are 3.52–9.46 mm and 3.44–10.85 mm, respectively. The foot measures 192.4 mm long, and the final soles measure 220.5 mm left and 218.0 mm right.

[Asset contract](asset_contract.json) · [Sole geometry](sole_geometry_check.json) · [Khronos validator](validator.json) · [Fit iteration data](fit_history.json)

## Vertex checker RESULT

| Case | Max vertices inside | Minimum signed distance (m) |
| --- | ---: | ---: |
| rest | 0 | 0.002394 |
| walk | 0 | 0.0024 |
| run | 0 | 0.0018 |
| wave | 0 | 0.0024 |
| jump | 0 | 0.0024 |
| idle | 0 | 0.0024 |
| nod | 0 | 0.0024 |
| dance | 0 | 0.0024 |

[Raw output](motion_check.txt) · [JSON](motion_check.json)

## Triangle-overlap checker RESULT

| Case | Max overlapping triangle pairs | Minimum signed distance (m) |
| --- | ---: | ---: |
| rest | 0 | 0.002394 |
| walk | 0 | 0.0018 |
| run | 0 | 0.0018 |
| wave | 0 | 0.0024 |
| jump | 0 | 0.0024 |
| idle | 0 | 0.0024 |
| nod | 0 | 0.0024 |
| dance | 0 | 0.0024 |

[Raw output](motion_check_tri.txt) · [JSON](motion_check_tri.json)

The 996-sample reimport sweep checks quarter frames of walk and run, half frames of the other five clips, and the supplied checker samples. It found zero interior vertices and zero overlapping pairs. The signed-distance minimum was 1.422 mm at walk frame 16.25.

[Dense check](dense_check.json) · [Walk](png/walk.png) · [Run](png/run.png) · [Wave](png/wave.png) · [Jump](png/jump.png)

## Skin-pixel gate and review

The Cycles CPU close-ups use a flat green body and opaque blue shoes. Each corresponding sole mask tags the candidate foot below rest Z = 0.041 m in green and the other body regions in red. The program counts visible green in the complete mask image, including pixels outside the shoe silhouette. The same view with the shoe hidden provided a positive control. Across 24 views (underside, outboard and inboard of eight walk/run cases), the count was **0 exposed foot pixels**. The set includes each side's peak-lift frame and four regression frames from the earlier sneaker work. A separate orthographic visibility sweep tested 120 additional views at integer walk/run frames with at least 10 mm of foot lift and also counted zero exposed foot pixels.

Independent visual inspection confirmed the purple and ivory construction, lateral stars, three straps per shoe, high-top tongues, and a rounded toe with no open notch in the reviewed views. The sampled lifted soles were opaque from beneath and from the side. Faceting remains visible on the collar, white midsole, and toe transition. An angular strap end is visible in the opposite view, and the preview reads as a more muted lavender than the reference.

[Pixel gate and PNG hashes](skin_check.json) · [Visibility sweep](visibility_sweep.json) · [Walk underside](png/walk_17_left_underside_flat_skin.png) · [Walk side](png/walk_31_right_side_flat_skin.png) · [Run underside](png/run_27_right_underside_flat_skin.png) · [Run inner side](png/run_19_left_inner_side_flat_skin.png)

## Ground plane and remaining fit details

The master plantar skin reaches Z = 0. The footbed requires clearance beneath it and the tread has positive thickness. Maintaining a continuous sole with those constraints places the outsole below the baseline. The lowest rest vertices are Z = −18.29 mm left and −16.10 mm right. The tread has a broad base with local relief and cross-step clearance offsets. The soles are bulkier than a uniform 3 mm overhang. There are five inherited nonmanifold edges in the upper seam geometry, outside the verified sole region.

## Reproduction

Run from this directory in Blender 5.1.2. The guarded command supplied with the task can use these arguments. Both checkers are run in memory with the supplied geometry, poses and reporting preserved. CPU Cycles replaces the headless Workbench block and the shared camera PNGs are written once.

```sh
blender -b -noaudio --python-exit-code 1 --python fit_shoes.py
blender -b -noaudio --python-exit-code 1 --python fit_shoes.py -- --checkers --checker-renders
blender -b -noaudio --python-exit-code 1 --python fit_shoes.py -- --inspect-blend --verify --visibility --renders
node work/validate_local.cjs
```

The delivered pair was built from the original source, master and motion files in a fresh Blender process. The final command uses the repository's installed Khronos validator offline.

| File | SHA-256 |
| --- | --- |
| Final module GLB | `4724bfd192cc5dbd7e72b19c3bd6fd36b3ba4f26ec8fc6498333fbb535339434` |
| Tripo Studio source GLB | `4b990f8192aa210352ee32d2e0df6adeb9874f87baa7afbbb5d46db7c5b8468f` |
| Master rigged body | `0339318b375836ab8891e49bda178da7e6f115e012e83385d9f8850949a7bd6f` |
| Motion GLB | `ffccda1ba2a50eb10948853e03d17f0d095cd9b953d644c03c4fb9cb95529410` |
| Purple star reference PNG | `046ce39fb5d0e7477143628fa6432fd26590b3d61d503afbb7c1a72b35dd5f67` |

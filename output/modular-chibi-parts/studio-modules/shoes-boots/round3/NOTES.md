# Tan lace-up boots v3

[Web GLB](shoes_boots_v3.glb) · [Editable Blender file](shoes_boots_v3.blend) · [Fit script](fit_shoes_v3.py) · [Final rest views](renders/shoes_boots_v3/rest_views.png) · [Final run frame 3](renders/shoes_boots_v3/run_3_toe.png)

The build starts with the [round 2 GLB](../round2/shoes_boots_v2.glb). The two dark outsole slits reproduced in a monochrome Cycles render. The v2 soles had folded, nearly coplanar surfaces. The welded v2 sole-zone boundary count was already zero. The build removes the folded exterior bottoms, bridges the cut rings to a continuous triangulated outsole, and tucks four liner vertices above the tread. It welds glTF vertex splits at 1 µm, closes the six upper and hardware rim loops, and recalculates outward smooth normals with a crisp lower tread edge. The run toe repair reshapes seven shared upper/welt vertices and removes the baked-in dark crease from 162 atlas texels while preserving the pale welt. [Fit report](fit_report.json)

The retained upper UVs use a 768 × 768 region of each 1024 × 1024 atlas. The other regions carry the reprojected rubber tread. The three maps have 12 px of UV padding on the upper atlas. The tread receives 18 propagation steps that fill projection gaps and protect the tile borders. The native file packs its textures and has the master's pose-bone rotation modes. The GLB embeds three JPEG atlases. [Native check](checks/native_blend.json) · [Asset contract](checks/asset_contract.json) · [Khronos validator](checks/khronos_validator.json)

## Asset gate

| Check | v2 | v3 |
| --- | ---: | ---: |
| Geometric boundary edges, image-left boot and hardware | 22 | 0 |
| Geometric boundary edges, image-right boot and hardware | 21 | 0 |
| Edges shared by more than two faces, both boots | 10 | 0 |
| Geometric boundary edges in the sole zone, both boots | 0 | 0 |
| Triangles | 3,437 | 3,472 |
| GLB bytes | 1,239,108 | 864,676 |
| Embedded atlases | 3 × 1024 × 1024 | 3 × 1024 × 1024 |
| Khronos errors / warnings | 0 / 0 | 0 / 0 |
| Joints | 65 | 65 |
| Maximum nonzero influences | 3 | 3 |

The v3 file is 0.825 MiB. Its joint order and inverse bind matrices match the source. Boundary counts use the mesh recovered from the GLB with a 1 µm position weld to join the separate indices required by UV and shading seams. The native mesh also has zero boundary edges. [Export topology](checks/export_topology.json) · [Native topology](checks/native_blend.json)

## Motion gate

Every one of the 14 clips passed at integer and half frames. The sweep included 1,623 samples including rest and measured a minimum of 0.917 mm at walk frame 16.5, above the 0.500 mm threshold. [Per-frame results](checks/half_frame_gate.json)

| Clip | Samples | Max inside vertices | Max overlapping triangle pairs | Minimum clearance (mm) | Closest frame |
| --- | ---: | ---: | ---: | ---: | ---: |
| rest | 1 | 0 | 0 | 2.853 | 1 |
| walk | 113 | 0 | 0 | 0.917 | 16.5 |
| run | 61 | 0 | 0 | 1.498 | 0 |
| wave | 129 | 0 | 0 | 2.853 | 0 |
| jump | 101 | 0 | 0 | 2.702 | 9 |
| idle | 177 | 0 | 0 | 2.853 | 0 |
| nod | 113 | 0 | 0 | 2.853 | 0 |
| dance | 129 | 0 | 0 | 2.869 | 0 |
| sit_down | 73 | 0 | 0 | 2.479 | 19.5 |
| sit_idle | 181 | 0 | 0 | 2.568 | 3 |
| stand_up | 61 | 0 | 0 | 2.483 | 13.5 |
| hold_item | 121 | 0 | 0 | 2.853 | 0 |
| hold_box | 121 | 0 | 0 | 2.853 | 0 |
| hold_bag | 121 | 0 | 0 | 2.853 | 0 |
| take_item | 121 | 0 | 0 | 2.853 | 0 |

All six supplied checker runs passed in their original frame ranges. The extra banks also retest the shared clips. The wrapper uses a smaller Cycles CPU preview in headless Blender. The separate half-frame sweep covers every integer and half frame for both collision predicates.

| Supplied checker bank | Vertex output | Triangle output |
| --- | --- | --- |
| Seven shared clips | [Log](checks/shared/vertex/motion_check_dense.txt) · [JSON](checks/shared/vertex/motion_check.json) | [Log](checks/shared/triangle/motion_check_tri.txt) · [JSON](checks/shared/triangle/motion_check.json) |
| Sit and hold | [Log](checks/sit_hold/vertex/motion_check.txt) · [JSON](checks/sit_hold/vertex/motion_check.json) · [Frames](checks/sit_hold/vertex/motion_check_frames.json) | [Log](checks/sit_hold/triangle/motion_check_tri.txt) · [JSON](checks/sit_hold/triangle/motion_check_tri.json) · [Frames](checks/sit_hold/triangle/motion_check_tri_frames.json) |
| Carry | [Log](checks/carry/vertex/motion_check.txt) · [JSON](checks/carry/vertex/motion_check.json) · [Frames](checks/carry/vertex/motion_check_frames.json) | [Log](checks/carry/triangle/motion_check_tri.txt) · [JSON](checks/carry/triangle/motion_check_tri.json) · [Frames](checks/carry/triangle/motion_check_tri_frames.json) |

## Visual review

The 16-sample, two-thread Cycles CPU renders share the same camera settings for v2 and v3. The rest sheet reads front, right side, left side, rear, top and underside. Both versions include the closest sampled run pose at frame 0 and the reported defect pose at frame 3. [v2 rest sheet](renders/shoes_boots_v2/rest_views.png) · [v3 rest sheet](renders/shoes_boots_v3/rest_views.png) · [v2 manifest](renders/shoes_boots_v2/manifest.json) · [v3 manifest](renders/shoes_boots_v3/manifest.json)

| Sole | v2 near-black outline pixels | v3 near-black outline pixels | v2 near-black pixels across sole | v3 near-black pixels across sole |
| --- | ---: | ---: | ---: | ---: |
| Image-left | 313 | 0 | 313 | 0 |
| Image-right | 1892 | 0 | 2510 | 0 |

The pixel count uses the matching 460 × 360 underside renders. A camera ray identifies the visible area for each sole. A near-black pixel has all three sRGB channels at or below code 24 of 255. The outline is the 40-pixel inner band from the ray-traced silhouette. [v2 underside](renders/shoes_boots_v2/underside.png) · [v3 underside](renders/shoes_boots_v3/underside.png)

The independent visual reviewer inspected the final 16-sample renders for GLB SHA-256 `0bba4366f7543325bae777cfdef3e0d9aeacc72d0a6e5a6957f81431632c700d`. Both soles showed continuous tread across the former black slits. The forward toe meets the welt across the flagged span in the full frame and close-up. Front, both sides, rear and top passed. The side views retain dark tread marks at the bottom edge. [Frame 0](renders/shoes_boots_v3/run_0_deepest.png) · [Frame 3](renders/shoes_boots_v3/run_3_deepest.png) · [v2 toe close-up](renders/shoes_boots_v2/run_3_toe.png) · [v3 toe close-up](renders/shoes_boots_v3/run_3_toe.png)

## Rebuild and verify

Run from this folder with the guarded local Blender 5.1.2 and the repository's installed Khronos validator. The build imports the v2 GLB directly. It uses the round 2 fit and verification scripts for master rig mounting and existing checker helpers. `blender-local` limits Blender to two threads and sets Blender's temporary folder to this directory.

```sh
zsh blender-local --python fit_shoes_v3.py
node package_web_glb.cjs
zsh blender-local --python verify_shoes_v3.py -- half-frames
zsh blender-local --python verify_shoes_v3.py -- topology
zsh blender-local --python verify_shoes_v3.py -- native
zsh blender-local --python verify_shoes_v3.py -- renders
for suite in shared sit_hold carry; do
  for mode in vertex triangle; do
    zsh blender-local --python verify_shoes_v3.py -- checker "$suite" "$mode"
  done
done
```

The fit script regenerates the intermediate JPEGs and `boots_export_raw.glb` for packaging. Each render manifest and gate report identifies the GLB it measured by SHA-256.

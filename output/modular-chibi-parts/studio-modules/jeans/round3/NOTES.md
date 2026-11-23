# Studio jeans round 3

**Pass.** The final GLB has zero inside vertices and zero garment–body triangle overlaps in all 824 sampled poses. The minimum signed distance is **0.654179 mm**, at run frame 0. No garment penetration remains at the sampled times.

## Scope

The editable Blender file and the Studio module GLB start from the round-2 Studio jeans. All motion evidence uses `body-fix/motion_fixed.glb` and the supplied rigged master. Both checkers reimport the delivered GLB, bind it to the master's 65-joint rig, preserve the pose-bone rotation modes, and use the first action slot for each clip. The sweep includes rest and every integer and intervening half frame, including both clip endpoints.

## Deliverables

- [jeans_v3.glb](jeans_v3.glb) is **3,346,588 bytes**, with 4,704 triangles, 4,170 exported vertices, one skinned garment mesh, 65 joints, at most four normalized influences per vertex, and zero embedded animations.
- [jeans_v3.blend](jeans_v3.blend) is **4,241,683 bytes**. The editable mesh reopened with the master rig binding and packed textures.
- The Tripo material retains its three 1024 × 1024 textures with byte-identical embedded images. All 4,045 distinct round-2 UV coordinates remain at the measured 0.000001 UV precision. The subdivided patches add 86 interpolated UV coordinates. [Export verification](export_check.json)
- Khronos glTF Validator 2.0.0-dev.3.10 reports **0 errors and 0 warnings**. [Validator output](gltf_validator.json)
- [Walk](walk.png) · [Run](run.png) · [Wave](wave.png) · [Jump](jump.png) · [Six-view rest sheet](six_view.png) · [Render frames and hashes](render_manifest.json)

The verified GLB SHA-256 is `e363de92c007a02faf7db3d9c9590f837fad54c0051f51a5fc3cdd8a4c7e5d9e`.

## Vertex checker RESULT

| Clip | Poses | Peak vertices inside | Min signed distance (mm) | Min frame |
| --- | ---: | ---: | ---: | ---: |
| rest | 1 | 0 | 1.590377 | 1 |
| walk | 113 | 0 | 0.655800 | 50 |
| run | 61 | 0 | 0.654179 | 0 |
| wave | 129 | 0 | 1.570784 | 19 |
| jump | 101 | 0 | 1.100073 | 8.5 |
| idle | 177 | 0 | 1.579568 | 0 |
| nod | 113 | 0 | 1.579568 | 0 |
| dance | 129 | 0 | 1.288504 | 45 |

[Vertex RESULT text](motion_check.txt) · [All poses and rest measurements](motion_check.json)

## Triangle checker RESULT

| Clip | Poses | Peak garment–body triangle pairs | Min signed vertex distance (mm) |
| --- | ---: | ---: | ---: |
| rest | 1 | 0 | 1.590377 |
| walk | 113 | 0 | 0.655800 |
| run | 61 | 0 | 0.654179 |
| wave | 129 | 0 | 1.570784 |
| jump | 101 | 0 | 1.100073 |
| idle | 177 | 0 | 1.579568 |
| nod | 113 | 0 | 1.579568 |
| dance | 129 | 0 | 1.288504 |

[Triangle RESULT text](motion_check_tri.txt) · [All garment–body pairs by pose](motion_check_tri.json)

## Rest clearance

All distances are in millimeters. No rest vertex exceeds the 30 mm limit. The waistband opening spans Z 406.4–430.5 mm. The right cuff spans Z 70.5–79.4 mm, and the left cuff spans Z 70.5–79.8 mm.

| Region | Vertices | Min | P10 | Median | P90 | P95 | Max |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| All | 4,170 | 1.590 | 3.496 | 9.319 | 14.950 | 17.764 | 29.756 |
| Crotch | 863 | 3.413 | 8.544 | 12.109 | 19.957 | 22.464 | 27.030 |
| Cuff | 498 | 5.354 | 7.615 | 10.174 | 11.997 | 12.372 | 15.003 |
| Front hips | 444 | 1.590 | 1.679 | 3.565 | 9.269 | 10.758 | 15.396 |
| Knee | 438 | 4.886 | 9.107 | 12.501 | 17.783 | 22.296 | 29.756 |
| Lower leg | 470 | 4.491 | 6.107 | 8.542 | 10.469 | 10.623 | 11.306 |
| Seat | 63 | 1.827 | 2.929 | 5.381 | 13.279 | 13.664 | 15.066 |
| Upper thigh | 423 | 1.599 | 4.122 | 9.117 | 14.858 | 17.764 | 25.083 |
| Waistband | 971 | 1.747 | 2.912 | 7.231 | 12.656 | 14.695 | 17.628 |

The six-view sheet and four posed renders were visually self-reviewed. The jeans retain the hip-height waist, ankle-length cuffs, and the original denim detailing. A local crease remains behind the right knee in the rest rear and side views.

## Fitting

The fit begins with the round-2 GLB and reuses its fitter's skinning, Laplacian smoothing, intersection-witness, and export routines. The main bake projects worst posed vertex and triangle-interior deficits back through the blended skin, targets a 2 mm separation where the pose permits, and bounds the rest position and clearance. Selected long edges and recurrent contact patches are subdivided with UV and weight interpolation. The remaining rear-waistband contacts use a local weight search on the adjacent pelvis, spine and upper-leg joints. The run knee correction maps a coherent posed patch displacement back to rest using the blended transforms from the deepest flexion frames. The candidate scoring preserves the 0.5–30 mm rest window and tests both collision metrics.

The final knee weight search cleared the last triangle pairs. Its rear-waistband follow-through raised the final minimum to the required floor while preserving the zero pair count. [Fit history](fit_history.json)

## Master body baseline

The independently evaluated body-only result matches the published body-only integer-frame counts on every frame. The neutral master contains 318 pairs, including 163 eyes/head, 60 shorts/legs, and 95 foot/toe pairs. Motion totals are 148,758 pairs at integer frames and 146,142 pairs at intervening half frames. The garment overlap counts include every pair formed by one jeans triangle and one master-body triangle. The body-only totals are recorded separately. [Body-only counts and neutral region pairs](body_baseline_comparison.json) · [Body baseline notes](../../../body-fix/NOTES.md)

## Reproduction

Use Blender 5.1.2 in background mode with the supplied guard library. Set `TMPDIR` to the round-3 directory before invoking Blender. All geometry, skin, collision measurements and PNGs use Blender Python. Khronos validation uses the repository's locally installed validator.

```sh
export TMPDIR="$PWD/"
export DYLD_INSERT_LIBRARIES="$GUARD"
run_blender() {
  "$BLENDER" -b -t 6 -noaudio --factory-startup --disable-autoexec --python-exit-code 1 --python "$@"
}
run_blender fit_jeans_r3.py
run_blender fit_jeans_r3.py -- --patches
run_blender fit_jeans_r3.py -- --local
run_blender fit_jeans_r3.py -- --waist-skin
run_blender fit_jeans_r3.py -- --waist-skin
run_blender fit_jeans_r3.py -- --knee-patch --posed-field
run_blender fit_jeans_r3.py -- --knee-patch --posed-field --adaptive-field --lower-knee
run_blender fit_jeans_r3.py -- --knee-patch --posed-field --adaptive-field --upper-knee
run_blender fit_jeans_r3.py -- --knee-skin
master=../../../master/GJH_Chibi_Master_rigged.blend
motion=../../../body-fix/motion_fixed.glb
run_blender motion_check.py -- "$master" "$motion" jeans_v3.glb "$PWD"
run_blender motion_check_tri.py -- "$master" "$motion" jeans_v3.glb "$PWD"
run_blender fit_jeans_r3.py -- --verify-export
run_blender fit_jeans_r3.py -- --body-baseline
run_blender fit_jeans_r3.py -- --renders
```

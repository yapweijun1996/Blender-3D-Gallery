# Studio jeans round 4

**The seven legacy clips and rest pass. The four new clips still fail the collision gate.** Both checks covered 1,260 sampled poses. Peak inside-vertex counts fell in all four new clips, with the largest triangle-count reduction in the seated clips.

## Deliverables

- The [skinned GLB](jeans_v4.glb) contains 4,704 triangles, one garment mesh, 65 joints, at most four normalized influences per vertex, and zero embedded animations. File size is **3,346,592 bytes**.
- The [editable Blender file](jeans_v4.blend) is **4,285,326 bytes**. It reopened with packed textures, the 65-joint armature binding, and the hidden master-body fitting reference.
- The Tripo material, texture and sampler definitions match round 3. Its three 1024 × 1024 image payloads are byte-identical and all 4,131 source UV coordinates are present at 0.000001 UV precision. The validator reports **0 errors and 0 warnings**. [Structural and material checks](export_check.json) · [Khronos report](gltf_validator.json)
- Rest signed clearance spans **0.867899–29.859904 mm**. The six orthographic views match the round-3 framing. The posed renders use the final lowest signed-distance frames, `sit_idle` 70 and `hold_item` 43. [Six views](six_view.png) · [Sit idle](sit_idle.png) · [Hold item](hold_item.png) · [Render manifest](render_manifest.json)

The delivered GLB SHA-256 is `38d1590de971066520a499d0c9aac1278ad1f791a2929d4fb0e1f1f9a352346e`. The source GLB SHA-256 is `e363de92c007a02faf7db3d9c9590f837fad54c0051f51a5fc3cdd8a4c7e5d9e`.

## Vertex checker

| Clip | Samples | Peak inside vertices | Min signed distance (mm) | Min frame |
| --- | ---: | ---: | ---: | ---: |
| rest | 1 | 0 | 0.867899 | 1 |
| walk | 113 | 0 | 0.655799 | 50 |
| run | 61 | 0 | 0.709886 | 8 |
| wave | 129 | 0 | 0.867896 | 0 |
| jump | 101 | 0 | 0.867902 | 0 |
| idle | 177 | 0 | 0.867896 | 0 |
| nod | 113 | 0 | 0.867896 | 0 |
| dance | 129 | 0 | 0.853021 | 40 |
| sit_down | 73 | 11 | -9.206189 | 36 |
| sit_idle | 181 | 8 | -10.443995 | 70 |
| stand_up | 61 | 11 | -9.206161 | 0 |
| hold_item | 121 | 6 | -5.434744 | 43 |

[RESULT text](motion_check.txt) · [Per-frame measurements](motion_check.json)

## Triangle-overlap checker

| Clip | Samples | Peak overlap pairs | Min signed distance (mm) | Min frame |
| --- | ---: | ---: | ---: | ---: |
| rest | 1 | 0 | 0.867899 | 1 |
| walk | 113 | 0 | 0.655799 | 50 |
| run | 61 | 0 | 0.709886 | 8 |
| wave | 129 | 0 | 0.867896 | 0 |
| jump | 101 | 0 | 0.867902 | 0 |
| idle | 177 | 0 | 0.867896 | 0 |
| nod | 113 | 0 | 0.867896 | 0 |
| dance | 129 | 0 | 0.853021 | 40 |
| sit_down | 73 | 97 | -9.206189 | 36 |
| sit_idle | 181 | 51 | -10.443995 | 70 |
| stand_up | 61 | 97 | -9.206161 | 0 |
| hold_item | 121 | 47 | -5.434744 | 43 |

[RESULT text](motion_check_tri.txt) · [Per-frame triangle overlap evidence](motion_check_tri.json)

The supplied checker results agree with the detailed results on the peak counts and minimum signed distances within 0.003 mm. [Legacy vertices](motion_check_legacy_supplied.json) · [Action-bank vertices](motion_check_added_supplied.json) · [Legacy triangle pairs](motion_check_tri_legacy_supplied.json) · [Action-bank triangle pairs](motion_check_tri_added_supplied.json)

## Remaining contacts

- `sit_down` — 9.206189 mm vertex penetration at frame 36, upper thigh / RightForeArm. Pair depths were upper thigh / RightForeArm 7.043397 mm at 33.5, waistband / RightForeArm 6.912142 mm at 2, upper thigh / RightHand 6.476941 mm at 33, waistband / LeftForeArm 6.155124 mm at 0, knee / RightHandThumb1 5.133925 mm at 34, knee / RightHand 4.571930 mm at 36, front hips / RightForeArm 4.352889 mm at 2.5, front hips / LeftForeArm 3.162351 mm at 3.5, seat / LeftForeArm 2.841317 mm at 3, upper thigh / RightHandThumb1 2.382389 mm at 33, upper thigh / RightUpLeg 2.243308 mm at 36, knee / RightUpLeg 2.242897 mm at 36, seat / RightForeArm 0.082539 mm at 0.
- `sit_idle` — 10.443995 mm vertex penetration at frame 70, upper thigh / RightForeArm. Pair depths were upper thigh / RightForeArm 7.198719 mm at 70, upper thigh / RightHand 5.075163 mm at 66, knee / RightHand 4.940191 mm at 8.5, knee / RightHandThumb1 4.940191 mm at 8.5, knee / RightForeArm 2.725387 mm at 21, upper thigh / RightHandThumb1 2.461751 mm at 52, upper thigh / RightUpLeg 2.243335 mm at 16.5, knee / RightUpLeg 2.242923 mm at 11.5.
- `stand_up` — 9.206161 mm vertex penetration at frame 0, upper thigh / RightForeArm. Pair depths were upper thigh / RightForeArm 7.091602 mm at 1.5, waistband / RightForeArm 6.911341 mm at 28.5, waistband / LeftForeArm 6.155124 mm at 30, upper thigh / RightHand 6.141147 mm at 2, knee / RightHandThumb1 5.370184 mm at 1, knee / RightHand 4.571942 mm at 0, front hips / RightForeArm 4.274594 mm at 28, front hips / LeftForeArm 3.080589 mm at 27.5, seat / LeftForeArm 2.896320 mm at 27.5, upper thigh / RightUpLeg 2.243332 mm at 0, knee / RightUpLeg 2.242922 mm at 0, upper thigh / RightHandThumb1 1.573717 mm at 2, seat / RightForeArm 0.082591 mm at 30.
- `hold_item` — 5.434744 mm vertex penetration at frame 43, waistband / LeftForeArm. Pair depths were waistband / LeftForeArm 7.175095 mm at 45, front hips / LeftForeArm 2.523574 mm at 40, seat / LeftForeArm 2.091211 mm at 40.

## Visual review

An independent image review found that the six rest views retain the straight, loose leg shape, the button and zipper, the pocket stitching, and the cuff hems. The side and rear three-quarter views show a slightly wavier waistband edge. The hold pose keeps the waist and cuffs legible. The seated image still has a rounded seat projection and an angular lower contour on the near side. A same-frame render of the shipped round-3 GLB shows that contour and the small crotch point in the same area. [Round 3 seated reference](round3_sit_idle_reference.png) · [Round 4 seated capture](sit_idle.png)

## Fitting and verification

The editable fit starts by importing `../round3/jeans_v3.glb`. The fitter bakes the worst posed contact directions using a 2 mm target margin, maps the offsets through the blended skin, and smooths their transitions while honoring the local projection constraints. Rest-shape guards constrain the edits. The final export keeps the checked byte representation of unaffected vertices and transfers only the two Blender-adjusted knee seam positions from the wider-step candidate. Coherent side-waist and thigh changes were followed by incident-triangle searches with the seven legacy clips checked throughout. The selected asset uses the original triangle count. The evaluated subdivision trials either reduced rest clearance too far or increased the remaining overlap count. [Fitting history](fit_history.json)

The same master and clip banks were used throughout. A body-only spot check found 42 left-upper-leg / left-forearm triangle overlaps at `hold_item` frame 43 and right-upper-leg overlaps with the right forearm, hand, and thumb at `sit_idle` frame 70. These are contacts already present in the posed master. The garment checks count all jeans–body pairs, including those near these contacts.

Both checks measure the exported GLB after a fresh import. The supplied checker adapter samples every integer and half frame and the clip endpoints, resets the neutral pose, keeps the first action slot, retains the full signed-distance precision, and omits Workbench previews. The independent detailed scan adds contact locations and separating depths. [Checker adapter](check_jeans_r4.py)

The largest triangle depth is the minimum rigid translation that separates a pair of zero-thickness triangles. The vertex checker reports the signed offset along the nearest body-face normal. The two depths measure different geometry.

The shoulder and upper-arm influences retained by the local search are small. The maximum per-vertex value is 3.52% at the right shoulder. The selected skin still uses up to four normalized influences per vertex.

## Reproduction

Set `BLENDER` and `GUARD` to the executable and guard library from the brief. Run from this directory. The checker adapter reads the supplied legacy scripts at their original scratchpad paths.

```sh
run_blender() {
  TMPDIR="$PWD/" BLENDER_USER_RESOURCES="$PWD/.blender" PYTHONDONTWRITEBYTECODE=1 \
    DYLD_INSERT_LIBRARIES="$GUARD" "$BLENDER" -b -t 6 -noaudio --factory-startup \
    --disable-autoexec --python-exit-code 1 --python "$@"
}
run_blender fit_jeans_r4.py
run_blender fit_jeans_r4.py -- --patches
run_blender fit_jeans_r4.py -- --local
run_blender fit_jeans_r4.py -- --preserve-legacy
run_blender fit_jeans_r4.py -- --strict-local
run_blender fit_jeans_r4.py -- --exact-legacy
run_blender check_jeans_r4.py -- detail
run_blender fit_jeans_r4.py -- --stabilize-floor --analytic
run_blender check_jeans_r4.py -- detail
run_blender fit_jeans_r4.py -- --stabilize-floor
run_blender check_jeans_r4.py -- detail
cp jeans_v4.glb .before-knee.glb
run_blender fit_jeans_r4.py -- --stabilize-floor --wider-step
cp jeans_v4.glb .after-knee.glb
run_blender fit_jeans_r4.py -- --stable-export .before-knee.glb .after-knee.glb
rm .before-knee.glb .after-knee.glb
for bank in detail legacy added; do
  run_blender check_jeans_r4.py -- "$bank"
  run_blender check_jeans_r4.py -- "$bank" --triangles
done
run_blender fit_jeans_r4.py -- --verify-export
run_blender render_jeans_r4.py
```

The local Khronos glTF Validator is in the repository's installed `node_modules/gltf-validator`. Blender Python produced the models, pose measurements, and renders. [Validator report](gltf_validator.json)

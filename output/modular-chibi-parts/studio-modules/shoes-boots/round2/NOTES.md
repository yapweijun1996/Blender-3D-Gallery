# Tan lace-up boots v2

[Web GLB](shoes_boots_v2.glb) · [Editable Blender scene](shoes_boots_v2.blend) · [Fit script](fit_shoes_v2.py) · [Six rest views](fit_views_v2.png) · [Corrected run frame 3](run_deepest_v2.png)

## Fit and web export

The input was the studio's [fitted v1 GLB](../shoes_boots_v1.glb), with the [original builder](../fit_shoes.py) and [v1 notes](../NOTES.md) as references. Against the corrected shared clips, v1 reached 44 interior exported vertices and 70 body/boot triangle-overlap pairs in run. Frame 3 was the deepest sample at −1.787 mm. [Original vertex report](../../../body-fix/sh-boots/motion_check_dense.txt) · [Original triangle report](../../../body-fix/sh-boots/motion_check_tri.txt)

The fit evaluated 61 integer and half frames of corrected run, from frame 0 to 30. It projected deficient vertices toward the exterior along the nearest body surface, using the signed depth and a 1.5 mm margin in each pose. It resolved residual triangle contacts at their crossing points and projected the Laplacian passes back onto the measured clearance constraints. Direct nearest-surface queries resolved final changes of nearest face. The movement clamp was 0–20 mm. Of the welded geometric vertices, 76 moved by more than 1 µm, with a maximum shift of 4.962 mm. Two local passes adjusted the weights of 176 vertices near the affected ankle and toe regions. The fitted run minimum was 1.500 mm before export. [Fit measurements](fit_report.json)

The GLB uses the v1 material parameters, texture roles, and UV layout. The native scene keeps the three source atlases packed and uses the master's pose-bone rotation modes. The GLB encodes the atlases at 1024 × 1024 with Blender JPEG quality 94. The packaging script restored one degenerate exported tangent from the v1 vertex with the same UV, then verified the resulting GLB with the local Khronos validator. [Native file check](checks/native_blend.json) · [Web contract](checks/asset_contract.json) · [Khronos report](checks/khronos_validator.json)

| Asset | Triangles | Bytes |
| --- | ---: | ---: |
| v1 GLB | 3,437 | 4,663,012 |
| v2 web GLB | 3,437 | 1,239,108 |
| v2 editable BLEND | 3,437 | 8,611,988 |

The web GLB contains one skinned mesh, one skin and 65 joints in v1 order. The inverse bind matrices match v1 exactly. It has a maximum of three nonzero weights per vertex, zero animations, and zero Khronos errors and warnings. The web payload is 1.182 MiB, 73.4% smaller than v1.

## Motion gate

Both supplied checkers passed for all 14 clips and rest. The independent half-frame sweep tested 1,623 poses on the final GLB. Its lowest clearance was 1.134 mm at walk frame 16.5. [Full half-frame measurements](checks/half_frame_gate.json)

| Pose or clip | Samples | Max vertices inside | Max overlap pairs | Min signed distance (mm) |
| --- | ---: | ---: | ---: | ---: |
| rest | 1 | 0 | 0 | 2.853 |
| walk | 113 | 0 | 0 | 1.134 |
| run | 61 | 0 | 0 | 1.498 |
| wave | 129 | 0 | 0 | 2.853 |
| jump | 101 | 0 | 0 | 2.702 |
| idle | 177 | 0 | 0 | 2.853 |
| nod | 113 | 0 | 0 | 2.853 |
| dance | 129 | 0 | 0 | 2.869 |
| sit_down | 73 | 0 | 0 | 2.474 |
| sit_idle | 181 | 0 | 0 | 2.568 |
| stand_up | 61 | 0 | 0 | 2.483 |
| hold_item | 121 | 0 | 0 | 2.853 |
| hold_box | 121 | 0 | 0 | 2.853 |
| hold_bag | 121 | 0 | 0 | 2.853 |
| take_item | 121 | 0 | 0 | 2.853 |

The supplied checkers use their original geometry predicates, sampling and render cameras. The wrapper switches the preview renderer to Cycles CPU for headless Blender 5.1.2. Each folder contains the original numeric results, available frame details, previews and input hashes.

| Bank | Vertex report | Triangle report |
| --- | --- | --- |
| Seven shared clips | [Log](checks/shared/vertex/motion_check_dense.txt) · [JSON](checks/shared/vertex/motion_check.json) | [Log](checks/shared/triangle/motion_check_tri.txt) · [JSON](checks/shared/triangle/motion_check.json) |
| Sit and hold | [Log](checks/sit_hold/vertex/motion_check.txt) · [JSON](checks/sit_hold/vertex/motion_check.json) · [Frames](checks/sit_hold/vertex/motion_check_frames.json) | [Log](checks/sit_hold/triangle/motion_check_tri.txt) · [JSON](checks/sit_hold/triangle/motion_check_tri.json) · [Frames](checks/sit_hold/triangle/motion_check_tri_frames.json) |
| Carry | [Log](checks/carry/vertex/motion_check.txt) · [JSON](checks/carry/vertex/motion_check.json) · [Frames](checks/carry/vertex/motion_check_frames.json) | [Log](checks/carry/triangle/motion_check_tri.txt) · [JSON](checks/carry/triangle/motion_check_tri.json) · [Frames](checks/carry/triangle/motion_check_tri_frames.json) |

## Appearance comparison

The rest sheet reads left to right, then top to bottom. It shows front, left three-quarter, right three-quarter, side, back and underside. The deepest-run image shows both boots on the master at the initial v1 penetration frame. Both versions use matched orthographic views, poses, lighting and Cycles CPU settings. [v1 six views](visual/fit_views_v1.png) · [v2 six views](fit_views_v2.png) · [v1 run frame 3](visual/run_deepest_v1.png) · [v2 run frame 3](run_deepest_v2.png) · [v2 view settings](visual/views_v2.json) · [v2 run-frame settings](visual/run_deepest_v2.json)

The first fit exposed a small orange triangle of lining below the right boot's rear collar. The final fit tucked that liner corner behind the original leather and repeated all 61 run fit samples. [Pre-correction render](visual/fit_views_before_collar_tuck.png)

An independent reviewer passed the final six views and matched run frame 3. The rear collar lip and heel leather read continuously again. The rounded toe, shaft proportions, tan leather, laces, eyelets, buckles, welt and outsole retained their appearance. The run image shows no visible new ankle or sole distortion. The reviewer matched both capture hashes to their manifests and to GLB SHA-256 `bcc5cc2e061ee5077e0dcdb2f79b260ebf2dd2b0bc60ef07694f035f9d88a2b2`. The visual judgment covers the surfaces seen in these Blender renders.

The lowest rest tread measures Z = −15.433 mm in the shared rig coordinates.

## Rebuild and recheck

Run these commands in this folder on the supplied Blender 5.1.2 host. The local launcher sets the guard library and keeps Blender temporary files in this folder. The packaging command uses the repository's installed Khronos validator. The three intermediate JPEGs and `boots_export_raw.glb` are regenerated by the fit script.

```sh
zsh blender-local -t 3 --python fit_shoes_v2.py
node package_web_glb.cjs
zsh blender-local -t 2 --python verify_shoes_v2.py -- native
for suite in shared sit_hold carry; do
  for mode in vertex triangle; do
    zsh blender-local -t 2 --python verify_shoes_v2.py -- checker "$suite" "$mode"
  done
done
zsh blender-local -t 2 --python verify_shoes_v2.py -- half-frames
for version in v1 v2; do
  zsh blender-local -t 3 --python verify_shoes_v2.py -- views "$version"
  zsh blender-local -t 3 --python verify_shoes_v2.py -- deepest "$version"
done
```

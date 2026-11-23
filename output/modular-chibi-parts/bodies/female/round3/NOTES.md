# Female jeans · round 3

[Female jeans v3](female-jeans-v3.glb) refits the top 25 mm of the waistband to the hip surface and blends the correction through the following 13 mm. The rim was smoothed locally and the waistband skin weights were fitted against contact witnesses from the motion bank. Static signed vertex clearance within the fitted band is **1.900–2.950 mm**, compared with **1.611–21.965 mm** in v2. [Fit measurements](waistband.json)

The GLB uses 4,168 triangles and three 1024 × 1024 textures. The index and UV buffers, inverse bind matrices, embedded textures and rig hierarchy match v2. [Khronos report](female-jeans-v3.validator.json)

## Motion and layering

The original checkers reimported the final GLB and tested all 14 clips at 30 fps on integer and half frames and the authored endpoints. There are 1,827 animation samples plus one rest sample. The limiting distance is **0.531294 mm** at frame **4.5** of `stand_up`. The peak inside, body overlap and layering counts all equal zero. The minimum cuff-to-sneaker collar gap along the shin axis is 7.928 mm in `run`. Khronos returned **0 errors and 0 warnings**.

| Clip | Samples | Inside | Body pairs | Min signed mm | T-shirt pairs | Sneaker pairs |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| rest | 1 | 0 | 0 | 1.023 | 0 | 0 |
| walk | 142 | 0 | 0 | 0.765 | 0 | 0 |
| run | 76 | 0 | 0 | 0.631 | 0 | 0 |
| wave | 161 | 0 | 0 | 1.011 | 0 | 0 |
| jump | 126 | 0 | 0 | 0.663 | 0 | 0 |
| idle | 221 | 0 | 0 | 1.011 | 0 | 0 |
| nod | 141 | 0 | 0 | 1.011 | 0 | 0 |
| dance | 161 | 0 | 0 | 0.768 | 0 | 0 |
| sit_down | 73 | 0 | 0 | 0.650 | 0 | 0 |
| sit_idle | 181 | 0 | 0 | 0.790 | 0 | 0 |
| stand_up | 61 | 0 | 0 | 0.531 | 0 | 0 |
| hold_item | 121 | 0 | 0 | 1.023 | 0 | 0 |
| hold_box | 121 | 0 | 0 | 1.011 | 0 | 0 |
| hold_bag | 121 | 0 | 0 | 1.011 | 0 | 0 |
| take_item | 121 | 0 | 0 | 1.011 | 0 | 0 |

[Body gate](checks/jeans/gate.json) · [Shared vertex checker](checks/jeans/shared/motion_check_dense.json) · [Shared triangle checker](checks/jeans/shared/motion_check_tri.json) · [Seated and item clips by frame](checks/jeans/act/motion_check_both_frames.json) · [Carry and take clips by frame](checks/jeans/act2/motion_check_both_frames.json) · [Layering](layering.json)

Final GLB SHA-256 `e1988aecbe6c10e0737ff650f6381ff24f2443e2cd6243e365ed4defe55d0a1b`. The fit, checker, validator and render manifests all identify these same bytes.

## Visual review

An independent reviewer compared all six rest renders with the round 2 captures using matched cameras and verified both render manifests against the actual GLBs and PNGs. The front rim follows the hips and the rear lip and front projection are gone in both profiles. The back retains the central rise and seam. The review found no visible skin penetration or collateral change to seams, hems, overall silhouette or texture. Minor waistband rippling and the existing leg folds remain.

[Front](renders/jeans/front.png) · [Front left](renders/jeans/front-left.png) · [Front right](renders/jeans/front-right.png) · [Left](renders/jeans/left.png) · [Right](renders/jeans/right.png) · [Back](renders/jeans/back.png) · [Render manifest](renders/jeans/views.json) · [Round 2 right profile](../round2/renders/jeans/right.png)

## Reproduce

Run these commands from this directory. The wrapper uses the supplied guarded Blender and limits the process to two threads.

```sh
./run_blender.sh fit_waistband.py
./run_blender.sh render_final.py
./run_blender.sh verify.py -- jeans
./run_blender.sh verify.py -- --layers
node validate.cjs female-jeans-v3.glb
```

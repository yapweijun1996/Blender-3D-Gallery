# Male body and garment fit · Round 2

**Motion gate PASS. Module gate FAIL. GLB validation PASS.**

## Motion

[motion_male_fixed.glb](motion_male_fixed.glb) carries the same 14 clip names, input time bounds, 65 joints, and bind hierarchy as round 1. The verification counts unordered epsilon-zero triangle pairs from the reimported male body. It excludes adjacent triangles across welded rest positions and any exact pair already present in that mesh's bind pose. The male bind had 0 such pairs. The neutral reference master has 318 non-adjacent bind pairs across 9 zones. Its triangle IDs belong to a different mesh. [Male body replay](qa/body.json) · [Neutral rest pair IDs and depths](qa/neutral_rest_pairs.json) · [Package validation](qa/gltf_validation.json)

Target regions cover arms, hands and fingers against the torso, head and legs, and shins against thighs. The target count also includes elbow and wrist folds, shoulder overlaps and foot-to-shin contacts. The Blender replay checked 3026 pose samples. The reported floor error is the absolute vertical distance from the ground at reference-derived support samples. Sole and horizontal ankle changes are measured against round 1 at the same support samples. Hip change compares the maximum absolute vertical difference in Hips position. Each clip includes endpoints and integer and half frames at 24 and 30 fps. Walk also includes the offset 30 fps grid measured from its first key. The render sheets align sample phase across the neutral reference, round-one male and round-two male. The male wave raises its hand higher in the round-one retarget. The pose is carried through in round two. The take-item elbow opens enough to move the right hand outward. The walk edit also releases the left thumb locally where it touched the skirt. The other 13 animation definitions and their sampled data remain byte-identical to the previously audited bank. [Walk channel audit](qa/walk_motion_proof.json)

| Clip | Samples | Target pairs | All pairs | Peak at one sample | Deepest (mm) | Planted error (mm) | Sole change (mm) | Ankle drift (mm) | Hip change (mm) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| idle | 353 | 0 | 0 | 0 | 0.0000 | 0.0900 | 0.0000 | 0.0000 | 0.0000 |
| walk | 337 | 0 | 1818 | 10 | 0.9447 | 0.4619 | 3.7374 | 0.0865 | 0.0001 |
| run | 121 | 0 | 2089 | 52 | 1.8722 | 0.2500 | 2.8542 | 0.0001 | 0.0000 |
| wave | 257 | 0 | 0 | 0 | 0.0000 | 0.0900 | 0.0000 | 0.0000 | 0.0000 |
| jump | 201 | 0 | 175 | 5 | 0.0037 | 0.0902 | 0.0001 | 0.0000 | 0.0000 |
| nod | 225 | 0 | 36 | 1 | 0.0073 | 0.0900 | 0.0000 | 0.0000 | 0.0000 |
| dance | 257 | 0 | 514 | 5 | 0.0132 | 0.2500 | 3.8012 | 0.0000 | 0.0000 |
| sit_down | 117 | 0 | 3962 | 141 | 3.5501 | 0.0902 | 0.0001 | 0.0001 | 0.0000 |
| sit_idle | 289 | 0 | 39386 | 140 | 2.4588 | 0.0901 | 0.0000 | 0.0000 | 0.0000 |
| stand_up | 97 | 0 | 3184 | 142 | 3.6039 | 0.0902 | 0.0001 | 0.0001 | 0.0000 |
| hold_item | 193 | 0 | 386 | 2 | 0.0000 | 0.0900 | 0.0000 | 0.0000 | 0.0000 |
| hold_box | 193 | 0 | 0 | 0 | 0.0000 | 0.0900 | 0.0000 | 0.0000 | 0.0000 |
| hold_bag | 193 | 0 | 0 | 0 | 0.0000 | 0.0900 | 0.0000 | 0.0000 | 0.0000 |
| take_item | 193 | 0 | 0 | 0 | 0.0000 | 0.0900 | 0.0000 | 0.0000 | 0.0000 |

[Walk](renders/motion/walk-before-after.png) · [Wave](renders/motion/wave-before-after.png) · [Run](renders/motion/run-before-after.png) · [Sit idle](renders/motion/sit_idle-before-after.png) · [Hold box](renders/motion/hold_box-before-after.png) · [Take item](renders/motion/take_item-before-after.png)

## Modules

The three v2 exports start from the round 1 male garments. Long edges were split with UV/material interpolation and new skin weights were smoothed across welded seams. The bind-space offset bake samples signed distance and interior probes on crossed triangles. Each violated clearance requests the limiting penetration plus 1.5 mm. The Laplacian passes preserve the selected correction along its direction. The bake caps displacement at 30 mm from the subdivided source and tests the result against the posed surface. Trials that introduced new crossings were rejected or reduced. Residual entries below show any clearance the tested solutions could not reach. The reported gate independently reimports the exported GLBs and replays both round 1 predicates at every sampled frame. The gate requires no negative signed vertices, no body/garment triangle contacts and at least 0.5 mm signed clearance.

| Asset | Triangles | Peak inside vertices | Peak triangle pairs | Min clearance (mm) | Failed samples | Gate | Audit | Renders |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |
| male-tshirt-v2.glb | 4943 | 1 | 0 | -0.4250 | 1 | VERTEX ALLOWANCE | [JSON](qa/modules/tshirt.json) | [Six views](renders/tshirt/six-views.png) |
| male-dress-v2.glb | 4359 | 2 | 8 | -4.7764 | 22 | FAIL | [JSON](qa/modules/dress.json) | [Six views](renders/dress/six-views.png) |
| male-jeans-v2.glb | 5615 | 3 | 4 | -2.5131 | 36 | FAIL | [JSON](qa/modules/jeans.json) | [Six views](renders/jeans/six-views.png) |
| male-hair-bob.glb | 2994 | 0 | 0 | 0.5837 | 0 | PASS | [JSON](qa/modules/hair-bob.json) | [Six views](renders/hair-bob/six-views.png) |
| male-hair-spiky.glb | 2972 | 0 | 0 | 2.6096 | 0 | PASS | [JSON](qa/modules/hair-spiky.json) | [Six views](renders/hair-spiky/six-views.png) |
| male-hair-sidepart.glb | 2982 | 0 | 0 | 0.8128 | 0 | PASS | [JSON](qa/modules/hair-sidepart.json) | [Six views](renders/hair-sidepart/six-views.png) |
| male-sneakers.glb | 3492 | 0 | 0 | 0.5092 | 0 | PASS | [JSON](qa/modules/sneakers.json) | [Six views](renders/sneakers/six-views.png) |

[T-shirt](male-tshirt-v2.glb) · [Dress](male-dress-v2.glb) · [Jeans](male-jeans-v2.glb) · [Outfits](renders/outfits.png) · [Render manifest](renders/manifest.json)

| Fit export | Triangles | Maximum bind offset (mm) | Search evidence |
| --- | ---: | ---: | --- |
| male-tshirt-v2.glb | 4943 | 12.0082 | [Fit history](qa/fit-tshirt.json) |
| male-dress-v2.glb | 4359 | 15.1017 | [Fit history](qa/fit-dress.json) |
| male-jeans-v2.glb | 5615 | 16.3779 | [Fit history](qa/fit-jeans.json) |

### Outfit layer checks

| Pose | Garment pair | Triangle pairs |
| --- | --- | ---: |
| idle_f24 | tshirt/jeans | 77 |
| idle_f24 | jeans/sneakers | 1383 |
| idle_f24 | dress/sneakers | 0 |
| rest | tshirt/jeans | 80 |
| rest | jeans/sneakers | 1383 |
| rest | dress/sneakers | 0 |

### GLB packages

| File | Bytes | Joints | Errors | Warnings |
| --- | ---: | ---: | ---: | ---: |
| motion_male_fixed.glb | 1962828 | 65 | 0 | 0 |
| male-tshirt-v2.glb | 1256804 | 65 | 0 | 0 |
| male-dress-v2.glb | 977812 | 65 | 0 | 0 |
| male-jeans-v2.glb | 1238960 | 65 | 0 | 0 |

## Residual body overlaps

| Clip | Dominant joint pair | Samples | Triangle pair occurrences | Deepest (mm) | Frame |
| --- | --- | ---: | ---: | ---: | ---: |
| walk | Head / Head | 313 | 313 | 0.0170 | 7 |
| walk | LeftToeBase / LeftToeBase | 337 | 1348 | 0.0131 | 9 |
| walk | Hips / Hips | 47 | 157 | 0.9447 | 9.4 |
| run | Head / Head | 114 | 114 | 0.0736 | 27 |
| run | LeftToeBase / LeftToeBase | 121 | 484 | 0.0058 | 14 |
| run | Hips / LeftUpLeg | 39 | 660 | 1.8722 | 3 |
| run | LeftUpLeg / LeftUpLeg | 33 | 305 | 0.6925 | 3 |
| run | RightUpLeg / RightUpLeg | 25 | 372 | 1.5446 | 26.8 |
| run | Hips / RightUpLeg | 15 | 154 | 1.3627 | 12 |
| jump | LeftToeBase / LeftToeBase | 44 | 136 | 0.0000 | 7 |
| jump | Head / Head | 39 | 39 | 0.0037 | 9 |
| nod | Head / Head | 36 | 36 | 0.0073 | 8 |
| dance | LeftToeBase / LeftToeBase | 117 | 416 | 0.0000 | 43.6 |
| dance | Head / Head | 98 | 98 | 0.0132 | 40 |
| sit_down | LeftToeBase / LeftToeBase | 72 | 246 | 0.0000 | 19.2 |
| sit_down | Head / Head | 84 | 84 | 0.0066 | 17.2 |
| sit_down | Hips / LeftUpLeg | 37 | 1708 | 3.5501 | 26.4 |
| sit_down | Hips / RightUpLeg | 36 | 1518 | 3.2465 | 26 |
| sit_down | RightUpLeg / RightUpLeg | 29 | 243 | 1.0432 | 28.8 |
| sit_down | LeftUpLeg / LeftUpLeg | 28 | 163 | 0.7193 | 28.8 |
| sit_idle | Head / Head | 183 | 183 | 0.0103 | 14.5 |
| sit_idle | Hips / LeftUpLeg | 289 | 17478 | 2.4588 | 56.8 |
| sit_idle | Hips / RightUpLeg | 289 | 14528 | 2.4328 | 52.8 |
| sit_idle | LeftUpLeg / LeftUpLeg | 289 | 3359 | 0.8238 | 17.6 |
| sit_idle | RightUpLeg / RightUpLeg | 289 | 3679 | 1.1398 | 18.4 |
| sit_idle | LeftToeBase / LeftToeBase | 40 | 159 | 0.0000 | 47.5 |
| stand_up | Head / Head | 72 | 72 | 0.0087 | 10.4 |
| stand_up | Hips / LeftUpLeg | 32 | 1390 | 3.6039 | 2 |
| stand_up | Hips / RightUpLeg | 30 | 1235 | 3.3192 | 2.4 |
| stand_up | LeftUpLeg / LeftUpLeg | 22 | 124 | 0.7193 | 0 |
| stand_up | RightUpLeg / RightUpLeg | 24 | 195 | 1.0432 | 0 |
| stand_up | LeftToeBase / LeftToeBase | 46 | 168 | 0.0000 | 7.2 |
| hold_item | LeftToeBase / LeftToeBase | 193 | 386 | 0.0000 | 0 |

## Module clearance shortfalls

The T-shirt qualifies for the requested vertex allowance. The tested offset, weight, topology and local search passes left 1 inside vertex occurrence with zero triangle contacts. The exact frame and depth are listed below.

| Asset | Clip | Minimum frame | Failed samples | Peak inside vertices | Peak triangle pairs | Min signed (mm) | Max pair depth (mm) |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| male-tshirt-v2.glb | run | 12 | 1 | 1 | 0 | -0.4250 | 0.0000 |
| male-dress-v2.glb | run | 22.5 | 15 | 2 | 8 | -2.4896 | 0.1507 |
| male-dress-v2.glb | sit_down | 16.5 | 3 | 1 | 0 | -4.5997 | 0.0000 |
| male-dress-v2.glb | stand_up | 11.5 | 4 | 1 | 0 | -4.7764 | 0.0000 |
| male-jeans-v2.glb | walk | 9 | 1 | 0 | 0 | 0.4607 | 0.0000 |
| male-jeans-v2.glb | run | 0.5 | 14 | 3 | 4 | -2.5131 | 0.3040 |
| male-jeans-v2.glb | sit_down | 20.5 | 13 | 1 | 0 | -1.4203 | 0.0000 |
| male-jeans-v2.glb | stand_up | 11.2 | 8 | 1 | 0 | -2.0361 | 0.0000 |

## Reproduction

The vertex and triangle results use the same signed-nearest-normal and triangle-overlap predicates as the round 1 copies in ../qa/checkers. Both predicates run on a shared Blender-evaluated pose. The per-clip and per-frame evidence is in qa/modules/.

Run Blender jobs with sh run.sh. The wrapper configures the guard, the scratch directory and two threads. The motion passes are motion_repair.py, leg_polish.py, floor_polish.py and shoe_guard.py following the sneaker replay. The fit history records the guarded displacement, local shape and weight trials, exact vertex search, triangle patch trials and witness subdivision. verify.py replays the body and modules. render_round2.py generates the Cycles sheets. The structural and Khronos report is generated by node validate.mjs. node summarize.mjs regenerates these tables. The round-one checker drivers also checked the sneakers before the thumb polish. The final Blender replay includes the amended walk. [Original checker replay](qa/supplied/sneakers)

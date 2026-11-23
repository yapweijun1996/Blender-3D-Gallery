# Female wardrobe 4

The gate covers rest and 1,827 animation samples from the supplied motion bank at 30 fps,
including integer and half frames and exact authored endpoints. It uses signed nearest-triangle
distance, with negative distances denoting inside vertices. The pair counts report garment–body
triangle overlap. Layer counts are reported separately in each gate JSON.

The retained GLBs, Khronos reports and render manifests identify the same bytes. A PASS requires
both the gate and the six-view self-review to pass. Rounds counts the reviewed attempts, and a
FAIL denotes a candidate retained for inspection.

| Item | Triangles | MiB | Peak inside | Peak pairs | Min signed mm | Rounds | Result | Six-view self-review |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| hoodie | 3,112 | 0.121 | 9 | 114 | -1.2372 | 3 | FAIL | The waist, pocket, cuffs and closed underarms read clearly. In profile the thick rear fold still looks like a padded roll. |
| skirt | 1,792 | 0.083 | 0 | 0 | 0.6831 | 3 | FAIL | The waist is smoother and the thighs clear the skirt, but the front edge still forms angular points in run and sit and the pleats read unevenly. |
| jacket | 2,276 | 0.101 | 22 | 212 | -11.6660 | 3 | FAIL | The open front, collar, zipper and wrist bands read clearly, but the T-shirt protrudes through both side panels and sleeve roots. |
| shorts | 3,152 | 0.126 | 0 | 0 | 0.7649 | 3 | FAIL | The leg openings stay clear in the reviewed poses, but the waistband has a broken-looking edge and the front cuffs have angular folds. |

## Files and findings

- **hoodie.** Retained round 3. The limiting frame was 16 in `sit_idle`. Peak layer pairs were jeans 20, sneakers 0, boots 0. Khronos reported 0 errors and 0 warnings. Gate findings are Posed body clearance, Shipped outfit layering. Rear hood thickness is 67.4 mm. The conservative head clearance bound is 1.500 mm. [GLB](hoodie.glb) · [frame gate](hoodie.gate.json) · [Khronos](hoodie.validator.json) · [six views](renders/hoodie/six-view.png) · [motion sheet](renders/hoodie/motion-six-view.png) · [render manifest](renders/hoodie/views.json)
- **skirt.** Retained round 3. The limiting frame was 16 in `sit_down`. Peak layer pairs were tshirt 0, sneakers 0, boots 0. Khronos reported 0 errors and 0 warnings. The numerical gate passed. This round's exported positions were checked and locally stabilized before review. [GLB](skirt.glb) · [frame gate](skirt.gate.json) · [Khronos](skirt.validator.json) · [six views](renders/skirt/six-view.png) · [motion sheet](renders/skirt/motion-six-view.png) · [render manifest](renders/skirt/views.json)
- **jacket.** Retained round 3. The limiting frame was 37.5 in `idle`. Peak layer pairs were jeans 24, tshirt 1316, sneakers 0, boots 0. Khronos reported 0 errors and 0 warnings. Gate findings are Posed body clearance, Shipped outfit layering. [GLB](jacket.glb) · [frame gate](jacket.gate.json) · [Khronos](jacket.validator.json) · [six views](renders/jacket/six-view.png) · [motion sheet](renders/jacket/motion-six-view.png) · [render manifest](renders/jacket/views.json)
- **shorts.** Retained round 3. The limiting frame was 6.5 in `jump`. Peak layer pairs were tshirt 0, sneakers 0, boots 0. Khronos reported 0 errors and 0 warnings. The numerical gate passed. The leg tube minimum signed distance is 1.5224 mm. This round's exported positions were checked and locally stabilized before review. The pattern uses the shipped female jeans for topology and weights, with a new body-fitted cut and cuff flare. [GLB](shorts.glb) · [frame gate](shorts.gate.json) · [Khronos](shorts.validator.json) · [six views](renders/shorts/six-view.png) · [motion sheet](renders/shorts/motion-six-view.png) · [render manifest](renders/shorts/views.json)

## Reproduce

Run `./run.sh build_wardrobe.py -- <item> <round>` from this directory. The launcher uses two threads.
With `--render-only` the command reimports and renders the existing candidate. Each item is built and
visually reviewed in order. Earlier GLBs, reports, review records and renders are in `attempts/`.

# Male wardrobe fitting

The candidates use the Studio male master and `../body_male.glb`. The motion bank is `../round2/motion_male_fixed.glb`. Source geometry and textures come from the neutral wardrobe. The copied build notes are in [NOTES.original.md](NOTES.original.md).

Each candidate was reimported into Blender for the all-pose gate. The reports include rest, source endpoints, and every integer and half frame on the 24 fps and 30 fps grids. Inside counts and signed distances follow the body surface normals. Triangle pairs are intersections at an individual pose. The final candidates were remeasured with the full, uncropped Blender body BVH. Earlier rounds retain their original gate records. Shoes were checked against the shipped T-shirt and jeans. The skirt and shorts were checked against the shipped T-shirt. Shoe sole heights are measured against the bare-foot datum. A shoe-floor target of −6.5 mm uses the shipped sneaker outsole as the height reference.

| Item | Triangles | MiB | Peak inside | Peak pairs | Min signed (mm) | Rounds used | Result |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| shoes-boots | 3472 | 1.144 | 15 | 98 | -5.3990 | 3 | FAIL |
| bottom-skirt | 5392 | 0.732 | 75 | 258 | -14.1309 | 3 | FAIL |
| bottom-shorts | 2780 | 0.264 | 2 | 6 | -1.8719 | 3 | FAIL |
| shoes-sandals | 3482 | 1.191 | 0 | 0 | 0.6089 | 3 | PASS |
| shoes-slipons | 3474 | 1.468 | 0 | 0 | 0.5606 | 3 | FAIL |
| shoes-hightop | 3383 | 1.199 | 23 | 107 | -8.8300 | 3 | FAIL |

A fresh Blender session replayed 174 witness poses and found 0 discrepancies against the final gates. [Witness replay](qa/witness-replay.json)

## Files

| Item | Evidence | Peak layer pairs |
| --- | --- | ---: |
| shoes-boots | [Review candidate (round 3)](shoes-boots-r3.glb) · [All poses](qa/shoes-boots.gate.json) · [Khronos](qa/shoes-boots.validator.json) · [Six views](renders/shoes-boots/six-views.png) | 365 |
| bottom-skirt | [Review candidate (round 3)](bottom-skirt-r3.glb) · [All poses](qa/bottom-skirt.gate.json) · [Khronos](qa/bottom-skirt.validator.json) · [Six views](renders/bottom-skirt/six-views.png) · [Motion witnesses](renders/bottom-skirt/motion-views.png) | 991 |
| bottom-shorts | [Review candidate (round 3)](bottom-shorts-r3.glb) · [All poses](qa/bottom-shorts.gate.json) · [Khronos](qa/bottom-shorts.validator.json) · [Six views](renders/bottom-shorts/six-views.png) | 71 |
| shoes-sandals | [GLB](shoes-sandals.glb) · [All poses](qa/shoes-sandals.gate.json) · [Khronos](qa/shoes-sandals.validator.json) · [Six views](renders/shoes-sandals/six-views.png) | 0 |
| shoes-slipons | [Review candidate (round 3)](shoes-slipons-r3.glb) · [All poses](qa/shoes-slipons.gate.json) · [Khronos](qa/shoes-slipons.validator.json) · [Six views](renders/shoes-slipons/six-views.png) | 7 |
| shoes-hightop | [Review candidate (round 3)](shoes-hightop-r3.glb) · [All poses](qa/shoes-hightop.gate.json) · [Khronos](qa/shoes-hightop.validator.json) · [Six views](renders/shoes-hightop/six-views.png) | 187 |

## Rounds

- **shoes-boots** · [R1](qa/shoes-boots-r1.gate.json) (41 inside, 35 body pairs, -4.4550 mm, 1442 layer pairs) · [R2](qa/shoes-boots-r2.gate.json) (97 inside, 270 body pairs, -14.2856 mm, 269 layer pairs) · [R3](qa/shoes-boots-r3.gate.json) (15 inside, 98 body pairs, -5.3990 mm, 365 layer pairs). Selected candidate failed body clearance (minimum in run at frame 6), layering (365 pairs peak in run), Khronos validator (ACCESSOR_VECTOR3_NON_UNIT). The six rest views show both soles at the same height. The back and side views show a rippled cuff edge where the boot meets the jeans.
- **bottom-skirt** · [R1](qa/bottom-skirt-r1.gate.json) (27 inside, 102 body pairs, -6.3692 mm, 1435 layer pairs) · [R2](qa/bottom-skirt-r2.gate.json) (28 inside, 102 body pairs, -6.3692 mm, 1435 layer pairs) · [R3](qa/bottom-skirt-r3.gate.json) (75 inside, 258 body pairs, -14.1309 mm, 991 layer pairs). Selected candidate failed body clearance (minimum in walk at frame 36.5), layering (991 pairs peak in sit_idle). The rest sheet shows the skirt opening and waistband beneath the shirt. The motion witnesses show the front hem lifting and pinching around the legs in run and sit_down.
- **bottom-shorts** · [R1](qa/bottom-shorts-r1.gate.json) (8 inside, 86 body pairs, -5.6004 mm, 92 layer pairs) · [R2](qa/bottom-shorts-r2.gate.json) (2 inside, 0 body pairs, -2.5995 mm, 85 layer pairs) · [R3](qa/bottom-shorts-r3.gate.json) (2 inside, 6 body pairs, -1.8719 mm, 71 layer pairs). Selected candidate failed body clearance (minimum in sit_down at frame 14.8), layering (71 pairs peak in sit_idle). The six rest views show a close waistband and clean leg openings, with some bunching at the inseam. The motion gate still finds body and T-shirt contact.
- **shoes-sandals** · [R1](qa/shoes-sandals-r1.gate.json) (0 inside, 4 body pairs, 0.7659 mm, 420 layer pairs) · [R2](qa/shoes-sandals-r2.gate.json) (3 inside, 11 body pairs, -0.9121 mm, 60 layer pairs) · [R3](qa/shoes-sandals-r3.gate.json) (0 inside, 0 body pairs, 0.6089 mm, 0 layer pairs). The rest views show aligned soles, exposed toes through the open fronts, and straps seated around the feet under the jean cuffs.
- **shoes-slipons** · [R1](qa/shoes-slipons-r1.gate.json) (2 inside, 23 body pairs, -0.3125 mm, 965 layer pairs) · [R2](qa/shoes-slipons-r2.gate.json) (65 inside, 146 body pairs, -8.9355 mm, 122 layer pairs) · [R3](qa/shoes-slipons-r3.gate.json) (0 inside, 0 body pairs, 0.5606 mm, 7 layer pairs). Selected candidate failed layering (7 pairs peak in run). The rest views show aligned soles and covered toes. The reshaped collars show abrupt outward folds in the front and side views.
- **shoes-hightop** · [R1](qa/shoes-hightop-r1.gate.json) (1 inside, 14 body pairs, -0.8090 mm, 1891 layer pairs) · [R2](qa/shoes-hightop-r2.gate.json) (26 inside, 105 body pairs, -8.8299 mm, 189 layer pairs) · [R3](qa/shoes-hightop-r3.gate.json) (23 inside, 107 body pairs, -8.8300 mm, 187 layer pairs). Selected candidate failed body clearance (minimum in walk at frame 16.5), layering (187 pairs peak in run). Both soles reach the common floor. The front, back and side views show a wrinkled, asymmetric collar and toe box after the cuff expansion.

Run `node batch_fit.mjs` to continue the ordered batch. Each item uses at most three candidate exports. The batch invokes one Blender process at a time, with two threads. Run `node report.mjs` to refresh this report.

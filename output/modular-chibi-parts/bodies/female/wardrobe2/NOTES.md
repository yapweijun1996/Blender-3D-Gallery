# Female modular wardrobe 2

The gate covers rest and 1,827 animation samples from the supplied 14-clip motion bank. It uses 30 fps, checks integer and half frames, and includes exact authored endpoints. The signed clearance follows the supplied nearest-triangle normal metric.

The shipped sneaker sole defines the common rest floor at −5.959 mm relative to the barefoot body origin. Both shoes must reach that plane within 0.5 mm. The renders use the same plane.

Layer tests use the shipped T-shirt, jeans and sneakers verified by hash. Shoes replace sneakers. Bottoms replace jeans. The garment peak columns report contacts with the body. Each gate JSON also reports layering by clip.

Each named GLB is the exact candidate used for its gate and renders. A FAIL GLB is an inspection candidate retained after the three-round limit. The matching gate declares its delivery status. Peaks and clearance describe the retained GLB. Rounds used counts all attempts for the item.

The female folder supplied the original fitter, launcher and notes. The sibling male folder supplied the three same-named gate, layer and batch entry points, which were adapted here to the female assets and sequential queue.

| Item | Triangles | MiB | Peak inside | Peak pairs | Min signed mm | Rounds used | Result |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| shoes-boots | 3,472 | 0.761 | 14 | 41 | -0.8226 | 3 | FAIL |
| bottom-skirt | 2,880 | 0.395 | 45 | 72 | -12.9963 | 3 | FAIL |
| bottom-shorts | 2,780 | 0.198 | 4 | 8 | -3.9843 | 3 | FAIL |
| shoes-sandals | 3,482 | 0.608 | 2 | 21 | -1.9396 | 3 | FAIL |
| shoes-slipons | 3,474 | 0.808 | 4 | 105 | -5.2840 | 3 | FAIL |
| shoes-hightop | 3,383 | 1.003 | 5 | 32 | -0.2020 | 3 | FAIL |
| hair-ponytail | 2,968 | 0.214 | 0 | 0 | 1.2973 | 2 | PASS |

## Files and findings

- **shoes-boots.** Round 3 retained. Minimum body clearance -0.8226 mm in `walk` at frame 52. Peak body overlap 41 pairs in `run` at frame 12.5. Both soles meet the common floor in rest. The compressed collars are visibly pinched and uneven. [fitted candidate](shoes-boots.glb) · [gate for all frames](shoes-boots.gate.json) · [Khronos](shoes-boots.validator.json) · [render manifest](renders/shoes-boots/views.json) · [front](renders/shoes-boots/front.png) · [front-left](renders/shoes-boots/front-left.png) · [left](renders/shoes-boots/left.png) · [back](renders/shoes-boots/back.png) · [right](renders/shoes-boots/right.png) · [front-right](renders/shoes-boots/front-right.png)
- **bottom-skirt.** Round 2 retained. Minimum body clearance -12.9963 mm in `sit_down` at frame 20.5. Peak body overlap 72 pairs in `run` at frame 4. The motion renders show the hem riding up and intersecting the thigh in run and sit_down. [fitted candidate](bottom-skirt.glb) · [gate for all frames](bottom-skirt.gate.json) · [Khronos](bottom-skirt.validator.json) · [render manifest](renders/bottom-skirt/views.json) · [front](renders/bottom-skirt/front.png) · [front-left](renders/bottom-skirt/front-left.png) · [left](renders/bottom-skirt/left.png) · [back](renders/bottom-skirt/back.png) · [right](renders/bottom-skirt/right.png) · [front-right](renders/bottom-skirt/front-right.png) · [walk, run and sit-down](renders/bottom-skirt/motion.png)
- **bottom-shorts.** Round 3 retained. Minimum body clearance -3.9843 mm in `stand_up` at frame 13. Peak body overlap 8 pairs in `run` at frame 13. The shorts keep a recognizable shape in rest. The waistband is uneven and the white base layer is exposed along the rim. [fitted candidate](bottom-shorts.glb) · [gate for all frames](bottom-shorts.gate.json) · [Khronos](bottom-shorts.validator.json) · [render manifest](renders/bottom-shorts/views.json) · [front](renders/bottom-shorts/front.png) · [front-left](renders/bottom-shorts/front-left.png) · [left](renders/bottom-shorts/left.png) · [back](renders/bottom-shorts/back.png) · [right](renders/bottom-shorts/right.png) · [front-right](renders/bottom-shorts/front-right.png)
- **shoes-sandals.** Round 3 retained. Minimum body clearance -1.9396 mm in `run` at frame 1. Peak body overlap 21 pairs in `run` at frame 1. Both soles reach the common floor. The side straps and heel loop kink outward in the side views. [fitted candidate](shoes-sandals.glb) · [gate for all frames](shoes-sandals.gate.json) · [Khronos](shoes-sandals.validator.json) · [render manifest](renders/shoes-sandals/views.json) · [front](renders/shoes-sandals/front.png) · [front-left](renders/shoes-sandals/front-left.png) · [left](renders/shoes-sandals/left.png) · [back](renders/shoes-sandals/back.png) · [right](renders/shoes-sandals/right.png) · [front-right](renders/shoes-sandals/front-right.png)
- **shoes-slipons.** Round 2 retained. Minimum body clearance -5.2840 mm in `walk` at frame 53. Peak body overlap 105 pairs in `run` at frame 27.5. The soles align with the floor tolerance. The side panels and heel seam are uneven in rest. [fitted candidate](shoes-slipons.glb) · [gate for all frames](shoes-slipons.gate.json) · [Khronos](shoes-slipons.validator.json) · [render manifest](renders/shoes-slipons/views.json) · [front](renders/shoes-slipons/front.png) · [front-left](renders/shoes-slipons/front-left.png) · [left](renders/shoes-slipons/left.png) · [back](renders/shoes-slipons/back.png) · [right](renders/shoes-slipons/right.png) · [front-right](renders/shoes-slipons/front-right.png)
- **shoes-hightop.** Round 3 retained. Minimum body clearance -0.2020 mm in `run` at frame 4.5. Peak body overlap 32 pairs in `run` at frame 17.5. Both soles meet the floor. The sole edge and upper panels remain visibly warped in rest. [fitted candidate](shoes-hightop.glb) · [gate for all frames](shoes-hightop.gate.json) · [Khronos](shoes-hightop.validator.json) · [render manifest](renders/shoes-hightop/views.json) · [front](renders/shoes-hightop/front.png) · [front-left](renders/shoes-hightop/front-left.png) · [left](renders/shoes-hightop/left.png) · [back](renders/shoes-hightop/back.png) · [right](renders/shoes-hightop/right.png) · [front-right](renders/shoes-hightop/front-right.png)
- **hair-ponytail.** Round 2 retained. The fringe and side hair follow the head without visible intersections. The full tail remains distinct from the neck and shoulders. [GLB](hair-ponytail.glb) · [gate for all frames](hair-ponytail.gate.json) · [Khronos](hair-ponytail.validator.json) · [render manifest](renders/hair-ponytail/views.json) · [front](renders/hair-ponytail/front.png) · [front-left](renders/hair-ponytail/front-left.png) · [left](renders/hair-ponytail/left.png) · [back](renders/hair-ponytail/back.png) · [right](renders/hair-ponytail/right.png) · [front-right](renders/hair-ponytail/front-right.png)

[Round results](results.json) · [Input motion audit](input-audit.json) · [Body surface audit](surface-audit.json) · [Original tool notes](NOTES.original.md)

Reproduce sequential fitting with `node batch_fit.mjs` in this directory. The Blender launcher is fixed at two threads.

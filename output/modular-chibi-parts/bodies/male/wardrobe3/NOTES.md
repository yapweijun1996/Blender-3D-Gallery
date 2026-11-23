# Male wardrobe · Body-derived shells

The source is `../body_male.glb` with the 65-joint bind from `../master_male.blend`. The geometry comes from clipped body triangles or sampled body cross-sections. Cut edges interpolate body weights, and a light smoothing pass keeps at most four influences. The skirt transfers weights at the waist and blends to the pelvis for the shared flare. The materials are flat PBR and contain no textures. Each bake samples the 14 clips in `../round2/motion_male_fixed.glb` and rest, including integer frames, half frames, and endpoints on the 24 and 30 fps grids. The skirt also clamps its flare against the all-pose thigh sweep in pelvis space. The bake preserves the largest required per-vertex correction through smoothing, with a 1.8 mm clearance margin. The gate reimports the exported GLB into Blender and evaluates the full body triangle BVH. It uses nearest-surface triangle normals for signed clearance.

The layering check uses the shipped GLBs from the demo manifest. Tops replace the T-shirt and pair with jeans and sneakers. Bottoms replace jeans and pair with the T-shirt and sneakers. Boots replace sneakers and pair with the T-shirt and jeans. Every sampled pose has separate overlap counts for each companion piece. The first hoodie trial used the timeline grids (2,915 samples). Later trials add the clip-relative grids (3,027 samples).

| Item | Triangles | MiB | Peak inside | Peak pairs | Min signed (mm) | Rounds | Result |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| top-hoodie | 2797 | 0.110 | 3 | 21 | -1.0038 | 3 | FAIL |
| top-jacket | 1029 | 0.059 | 3 | 25 | -1.1337 | 3 | FAIL |
| bottom-shorts | 946 | 0.055 | 8 | 147 | -3.1726 | 3 | FAIL |
| bottom-skirt | 1792 | 0.076 | 11 | 165 | -8.0573 | 3 | FAIL |
| shoes-boots | 1703 | 0.077 | 0 | 0 | 0.9123 | 2 | PASS |

## Files

- **top-hoodie** · [Review candidate](top-hoodie-r3.glb) · [Full gate](qa/top-hoodie.gate.json) · [Khronos](qa/top-hoodie-r3.validator.json) · [Six views](renders/top-hoodie/six-views.png)
- **top-jacket** · [Review candidate](top-jacket-r1.glb) · [Full gate](qa/top-jacket.gate.json) · [Khronos](qa/top-jacket-r1.validator.json) · [Six views](renders/top-jacket/six-views.png)
- **bottom-shorts** · [Review candidate](bottom-shorts-r3.glb) · [Full gate](qa/bottom-shorts.gate.json) · [Khronos](qa/bottom-shorts-r3.validator.json) · [Six views](renders/bottom-shorts/six-views.png)
- **bottom-skirt** · [Review candidate](bottom-skirt-r3.glb) · [Full gate](qa/bottom-skirt.gate.json) · [Khronos](qa/bottom-skirt-r3.validator.json) · [Six views](renders/bottom-skirt/six-views.png)
- **shoes-boots** · [GLB](shoes-boots.glb) · [Full gate](qa/shoes-boots.gate.json) · [Khronos](qa/shoes-boots-r2.validator.json) · [Six views](renders/shoes-boots/six-views.png)

## Round evidence

- **top-hoodie** · [R1](qa/top-hoodie-r1.gate.json) (15 inside, 92 body pairs, -4.6589 mm, layer peaks male-bottom-jeans.glb 0, male-shoes-sneakers.glb 0, Khronos 0/0, missed inside, pairs, signed_clearance) · [R2](qa/top-hoodie-r2.gate.json) (23 inside, 323 body pairs, -22.1297 mm, layer peaks male-bottom-jeans.glb 0, male-shoes-sneakers.glb 0, Khronos 0/0, missed inside, pairs, signed_clearance) · [R3](qa/top-hoodie-r3.gate.json) (3 inside, 21 body pairs, -1.0038 mm, layer peaks male-bottom-jeans.glb 0, male-shoes-sneakers.glb 0, Khronos 0/0, missed inside, pairs, signed_clearance)
- **top-jacket** · [R1](qa/top-jacket-r1.gate.json) (3 inside, 25 body pairs, -1.1337 mm, layer peaks male-bottom-jeans.glb 0, male-shoes-sneakers.glb 0, Khronos 0/0, missed inside, pairs, signed_clearance) · [R2](qa/top-jacket-r2.gate.json) (3 inside, 39 body pairs, -0.8362 mm, layer peaks male-bottom-jeans.glb 0, male-shoes-sneakers.glb 0, Khronos 0/0, missed inside, pairs, signed_clearance) · [R3](qa/top-jacket-r3.gate.json) (4 inside, 44 body pairs, -1.9590 mm, layer peaks male-bottom-jeans.glb 0, male-shoes-sneakers.glb 0, Khronos 0/0, missed inside, pairs, signed_clearance)
- **bottom-shorts** · [R1](qa/bottom-shorts-r1.gate.json) (24 inside, 518 body pairs, -10.6712 mm, layer peaks male-top-tshirt.glb 29, male-shoes-sneakers.glb 0, Khronos 0/0, missed inside, pairs, signed_clearance, layering) · [R2](qa/bottom-shorts-r2.gate.json) (28 inside, 476 body pairs, -4.2739 mm, layer peaks male-top-tshirt.glb 35, male-shoes-sneakers.glb 0, Khronos 0/0, missed inside, pairs, signed_clearance, layering) · [R3](qa/bottom-shorts-r3.gate.json) (8 inside, 147 body pairs, -3.1726 mm, layer peaks male-top-tshirt.glb 20, male-shoes-sneakers.glb 0, Khronos 0/0, missed inside, pairs, signed_clearance, layering)
- **bottom-skirt** · [R1](qa/bottom-skirt-r1.gate.json) (21 inside, 195 body pairs, -20.4786 mm, layer peaks male-top-tshirt.glb 37, male-shoes-sneakers.glb 0, Khronos 0/0, missed inside, pairs, signed_clearance, layering) · [R2](qa/bottom-skirt-r2.gate.json) (27 inside, 255 body pairs, -12.7644 mm, layer peaks male-top-tshirt.glb 0, male-shoes-sneakers.glb 0, Khronos 0/0, missed inside, pairs, signed_clearance) · [R3](qa/bottom-skirt-r3.gate.json) (11 inside, 165 body pairs, -8.0573 mm, layer peaks male-top-tshirt.glb 37, male-shoes-sneakers.glb 0, Khronos 0/0, missed inside, pairs, signed_clearance, layering)
- **shoes-boots** · [R1](qa/shoes-boots-r1.gate.json) (2 inside, 16 body pairs, -0.3683 mm, layer peaks male-bottom-jeans.glb 0, male-top-tshirt.glb 0, Khronos 0/0, missed inside, pairs, signed_clearance) · [R2](qa/shoes-boots-r2.gate.json) (0 inside, 0 body pairs, 0.9123 mm, layer peaks male-bottom-jeans.glb 0, male-top-tshirt.glb 0, Khronos 0/0)

## Failed clearance witnesses

- **top-hoodie** · -1.0038 mm in `run` at frame 18 · 21 body overlap pairs in `wave`.
- **top-jacket** · -1.1337 mm in `run` at frame 18 · 25 body overlap pairs in `run`.
- **bottom-shorts** · -3.1726 mm in `sit_down` at frame 25 · 147 body overlap pairs in `stand_up` · 20 outfit overlap pairs in `sit_idle`.
- **bottom-skirt** · -8.0573 mm in `wave` at frame 36.8 · 165 body overlap pairs in `wave` · 37 outfit overlap pairs in `run`.

The selected skirt also shows visible buckling at the side panels and hem in the six-view render.

The boots retain visible toe contours and a serrated color boundary at the cuff.

Rebuild a candidate with `./run.sh build_wardrobe.py -- ITEM ROUND`. Run `python3 results.py ITEM ROUND` for validation, then `./run.sh render_item.py -- FILE ITEM` for the selected GLB. Use `python3 results.py notes` to regenerate this table.

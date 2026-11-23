# Male wardrobe round 4

Each selected GLB is linked to its reimport gate and render manifest by SHA-256. The gate checks Blender deformation at rest and across 14 clips on 24 and 30 fps integer and half-frame timeline and clip-relative grids. Layering uses shipped male modules. The visual column is the author’s self-review of the exported GLB.

| Item | Triangles | MiB | Peak inside | Peak pairs | Min signed (mm) | Rounds | Result | Render observation |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| top-hoodie | 4569 | 0.155 | 14 | 110 | -14.442 | 3 | FAIL | The cowl, pocket and continuous underarms read clearly. Small cuff points remain in the motion sheet. |
| bottom-skirt | 2880 | 0.107 | 45 | 134 | -8.730 | 3 | FAIL | The hem is continuous and pleated. In the run sample, skin shows at the waistband. |
| top-jacket | 2407 | 0.101 | 18 | 193 | -14.268 | 3 | FAIL | Open zipper bands reveal the T-shirt. The underarms are continuous in the sheets, with small cuff notches. |
| bottom-shorts | 1285 | 0.069 | 12 | 43 | -5.369 | 3 | FAIL | The two cuffs read clearly, with a small front pucker. The seated rear shows a gray underlayer at the waistband. |

## Files

- **top-hoodie** · [GLB](top-hoodie.glb) · [Gate](qa/top-hoodie.gate.json) · [Khronos](qa/top-hoodie.validator.json) · [Six views](renders/top-hoodie-r3/six-views.png) · [Motion views](renders/top-hoodie-r3/motion-views.png) · [Render manifest](renders/top-hoodie-r3/manifest.json) · Open gates: inside, pairs, signed clearance, layering.
- **bottom-skirt** · [GLB](bottom-skirt.glb) · [Gate](qa/bottom-skirt.gate.json) · [Khronos](qa/bottom-skirt.validator.json) · [Six views](renders/bottom-skirt-r3/six-views.png) · [Motion views](renders/bottom-skirt-r3/motion-views.png) · [Render manifest](renders/bottom-skirt-r3/manifest.json) · Open gates: inside, pairs, signed clearance, layering.
- **top-jacket** · [GLB](top-jacket.glb) · [Gate](qa/top-jacket.gate.json) · [Khronos](qa/top-jacket.validator.json) · [Six views](renders/top-jacket-r3/six-views.png) · [Motion views](renders/top-jacket-r3/motion-views.png) · [Render manifest](renders/top-jacket-r3/manifest.json) · Open gates: inside, pairs, signed clearance, layering.
- **bottom-shorts** · [GLB](bottom-shorts.glb) · [Gate](qa/bottom-shorts.gate.json) · [Khronos](qa/bottom-shorts.validator.json) · [Six views](renders/bottom-shorts-r3/six-views.png) · [Motion views](renders/bottom-shorts-r3/motion-views.png) · [Render manifest](renders/bottom-shorts-r3/manifest.json) · Open gates: inside, pairs, signed clearance, leg clearance.

## Additional measurements

- The selected hoodie cowl is 85.0 mm deep in the center-back slice of the saved fit mesh. Its minimum sampled vertex-to-head distance is 1.680 mm.
- The selected skirt has 16 geometric pleats and a 290 mm bind-space hem height.
- The selected shorts have minimum signed clearances of -1.610 mm on the left leg and -5.369 mm on the right. The shipped T-shirt has zero overlap pairs with this candidate.
- All four selected exports have zero overlap pairs with both shipped footwear options. Each file is texture-free and has zero Khronos validator errors and warnings.
- The selected hoodie was rechecked from its existing GLB after the first gate run could not serialize an optional fitting statistic.

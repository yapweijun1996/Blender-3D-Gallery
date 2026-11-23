# Female modular wardrobe 3

New surfaces start from the exported female body. The motion gate uses the female master
and the 14-clip bank at 30 fps with 0.5-frame steps, authored endpoints, and rest.
Clearance is the signed nearest-triangle distance. Each garment uses flat PBR materials.
Each gate reports triangle contacts against the compatible shipped slots. All five retained files passed
their triangle, file size, texture and Khronos limits. Every retained file uses the female bind and 65
mixamorig joints, with up to four normalized influences per vertex. A FAIL marks a retained
inspection candidate.

Hoodie, jacket, shorts and boots start as masked patches of the female skin. The hood follows the
back of the scalp, the jacket has a cut front opening, and the boot soles have extra thickness.
The skirt loft starts from female body cross sections, with a radial clamp sampled against the
moving lower body. The 1.8 mm bake target uses the worst vertex and triangle contact witnesses
over the full frame grid. The exported-file gate uses a 0.5 mm minimum.

| Item | Triangles | MiB | Peak inside | Peak pairs | Min signed mm | Rounds | Result |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| hoodie | 2,195 | 0.103 | 0 | 0 | 0.5523 | 3 | PASS |
| jacket | 1,328 | 0.075 | 0 | 0 | 0.2208 | 3 | FAIL |
| shorts | 864 | 0.058 | 8 | 72 | -0.7815 | 3 | FAIL |
| skirt | 2,400 | 0.106 | 1 | 0 | -1.2848 | 3 | FAIL |
| boots | 1,546 | 0.077 | 0 | 0 | 0.6587 | 1 | PASS |

## Files and findings

- **hoodie.** Retained round 3. The raised hood and underarm vents are visible in rest. Minimum clearance was 0.5523 mm in `walk` at frame 66. Peak layer pairs were jeans 0, sneakers 0. [GLB](hoodie.glb) · [gate](hoodie.gate.json) · [Khronos](hoodie.validator.json) · [six views](renders/hoodie/views.json)
- **jacket.** Retained round 3. The open front and underarm cutouts are visible in rest. Two `run` samples missed the clearance threshold, at frames 16 and 22. The minimum was 0.2208 mm at frame 22. Peak layer pairs were jeans 0, sneakers 0. [GLB](jacket.glb) · [gate](jacket.gate.json) · [Khronos](jacket.validator.json) · [six views](renders/jacket/views.json)
- **shorts.** Retained round 3. The inseam relief shows the underlying body fabric in rest. Hip and inner-thigh contact remained. The minimum was -0.7815 mm in `sit_down` at frame 32.5, and the pair peak was 72 at frame 27.5. Peak layer pairs were tshirt 0, sneakers 0. [GLB](shorts.glb) · [gate](shorts.gate.json) · [Khronos](shorts.validator.json) · [six views](renders/shorts/views.json)
- **skirt.** Retained round 3. The shortened flared hem exposes the body's existing shorts material in rest. The gate flagged one inside vertex at `walk` frame 57.5 with -1.2848 mm signed clearance, and 19 samples fell below 0.5 mm. Triangle overlap was zero throughout. Peak layer pairs were tshirt 0, sneakers 0. [GLB](skirt.glb) · [gate](skirt.gate.json) · [Khronos](skirt.validator.json) · [six views](renders/skirt/views.json)
- **boots.** Retained round 1. Minimum clearance was 0.6587 mm in `run` at frame 4.5. The soles follow the body's toe contours and extend 2.93 mm below the shipped sneaker plane in rest. Peak layer pairs were tshirt 0, jeans 0. [GLB](boots.glb) · [gate](boots.gate.json) · [Khronos](boots.validator.json) · [six views](renders/boots/views.json)

[All round summaries](results.json)

Resume with `./run.sh wardrobe.py`. The launcher uses two threads. Archived rounds in `attempts/` keep the GLBs, frame gates and validator reports used for selection.

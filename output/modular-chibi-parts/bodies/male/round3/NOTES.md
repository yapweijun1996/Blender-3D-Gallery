# Male dress and jeans · Round 3

**Garment/body gates Pass. Outfit layer check Pass.** The Blender replay covered 3,026 samples across fourteen clips plus the bind pose. Sampling includes endpoints and integer and half frames on the round-two 24 and 30 fps grids.

| Export | Peak inside | Peak pairs | Min signed (mm) | Failed samples | Triangles | MiB | Max texture | Khronos E/W |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| [male-dress-v3.glb](male-dress-v3.glb) | 0 | 0 | 0.5774 | 0 | 4361 | 0.933 | 1024 px | 0/0 |
| [male-jeans-v3.glb](male-jeans-v3.glb) | 0 | 0 | 0.5472 | 0 | 4686 | 1.128 | 1024 px | 0/0 |

[Per-frame dress replay](qa/modules/dress.json) · [Per-frame jeans replay](qa/modules/jeans.json) · [Khronos and rig validation](qa/gltf_validation.json)

## Clip results

| Clip | Samples | Dress inside / pairs | Dress min (mm) | Jeans inside / pairs | Jeans min (mm) |
| --- | ---: | ---: | ---: | ---: | ---: |
| rest | 1 | 0/0 | 1.7991 | 0/0 | 0.8029 |
| idle | 353 | 0/0 | 0.7912 | 0/0 | 0.8030 |
| walk | 337 | 0/0 | 0.6883 | 0/0 | 0.6291 |
| run | 121 | 0/0 | 0.5774 | 0/0 | 0.5472 |
| wave | 257 | 0/0 | 0.9138 | 0/0 | 0.8030 |
| jump | 201 | 0/0 | 0.6102 | 0/0 | 0.7728 |
| nod | 225 | 0/0 | 0.9958 | 0/0 | 0.8030 |
| dance | 257 | 0/0 | 0.6381 | 0/0 | 0.6252 |
| sit_down | 117 | 0/0 | 0.6069 | 0/0 | 0.5749 |
| sit_idle | 289 | 0/0 | 0.8303 | 0/0 | 0.6094 |
| stand_up | 97 | 0/0 | 0.7644 | 0/0 | 0.6080 |
| hold_item | 193 | 0/0 | 1.4143 | 0/0 | 0.8030 |
| hold_box | 193 | 0/0 | 1.4472 | 0/0 | 0.8030 |
| hold_bag | 193 | 0/0 | 1.4160 | 0/0 | 0.8030 |
| take_item | 193 | 0/0 | 1.4875 | 0/0 | 0.8030 |

## Dress and jeans exceptions

None. Every sample met the 0.5000 mm signed-distance floor and both zero-contact predicates.

## Outfit fit

| Pose | Pair | Round 2 | Round 3 |
| --- | --- | ---: | ---: |
| rest | tshirt/jeans | 80 | 0 |
| rest | jeans/sneakers | 1383 | 0 |
| rest | dress/sneakers | 0 | 0 |
| idle_f24 | tshirt/jeans | 77 | 0 |
| idle_f24 | jeans/sneakers | 1383 | 0 |
| idle_f24 | dress/sneakers | 0 | 0 |

The original cuff is shortened to clear the sneaker opening, leaving a small visible ankle gap. The jeans waistband is inset locally by 2 mm. The final idle renders were visually checked from all six views and in both outfits.

[Dress six views](renders/dress/six-views.png) · [Jeans six views](renders/jeans/six-views.png) · [Both outfits](renders/outfits.png) · [Render hashes](renders/manifest.json)

## Fit and reproduction

The fit starts from the v2 exports, subdivides long edges on reported contact faces and clips the cuffs at 0.121 m in bind space. The offset bake converts each sampled limiting nearest-surface direction to bind space, adds a 2 mm margin and caps the displacement at 30 mm. The Laplacian pass preserves the required directional projection before capped trial selection. Local lofts and skin-weight blends are checked on the moving rig. The smallest positional edits preserve the GLB skin attributes. The final search also tests the normals of equally near triangles at shared body corners. The final audit reimports the delivered files and runs the round-two checker functions unchanged.

- dress displacement bound 8.074 mm. [Fit history](qa/fit-dress.json)
- jeans displacement bound 18.242 mm. [Fit history](qa/fit-jeans.json)

Replay with `sh blender.sh verify_round3.py --` and render with `sh blender.sh render_round3.py --`. Run `node package_round3.mjs` before replay to normalize the GLB roots and check the deliverable packages. [Bind offset measurements](qa/offset_measurement.json)

## Round-two carryovers

The accepted T-shirt has 1 inside vertex at run frame 12, -0.4250 mm signed, and 0 triangle pairs at that frame. The reused motion bank has 0 targeted body self-contact pairs in the round-two replay. The broader self-overlap diagnostic counted 51,550 pair occurrences. [T-shirt replay](../round2/qa/modules/tshirt.json) · [Body replay](../round2/qa/body.json)

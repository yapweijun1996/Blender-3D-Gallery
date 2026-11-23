# Female modular garments · round 2

This round uses the first-round [female body](../body_female.glb), [female motion bank](../motion_female.glb), [female master](../master_female.blend) and the round-one local checkers. The motion bank SHA-256 is `a393e8e8d31a2df5854b8e77a7fab27933e451a5215df5a321052dbc16915b8b`. All 175 first-round files matched their [pre-fit hashes](checks/round1-inputs.json).

## Body and asset checks

The vertex and triangle tests ran on each imported GLB at 30 fps, at integer and half frames and the authored endpoints. The checkers' combined output includes rest and the fourteen named clips. The 0.500 mm minimum applies to the three v2 garments.

| Module and proof | Triangles | MiB | Max texture px | Peak inside vertices | Peak overlap pairs | Min signed mm | Khronos errors / warnings | Gate |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| [female-tshirt-v2.glb](female-tshirt-v2.glb) · [checks](checks/tshirt/gate.json) | 4,225 | 0.772 | 1024 | 0 | 0 | 0.564 (run) | 0 / 0 | PASS |
| [female-dress-v2.glb](female-dress-v2.glb) · [checks](checks/dress/gate.json) | 4,042 | 0.556 | 1024 | 0 | 0 | 0.573 (walk) | 0 / 0 | PASS |
| [female-jeans-v2.glb](female-jeans-v2.glb) · [checks](checks/jeans/gate.json) | 4,168 | 0.688 | 1024 | 0 | 0 | 0.524 (sit_down) | 0 / 0 | PASS |
| [female-hair-bob.glb](../female-hair-bob.glb) · [checks](checks/hair-bob/gate.json) | 2,994 | 0.176 | 1024 | 0 | 0 | 1.210 (dance) | 0 / 0 | PASS |
| [female-hair-spiky.glb](../female-hair-spiky.glb) · [checks](checks/hair-spiky/gate.json) | 2,972 | 0.750 | 1024 | 0 | 0 | 1.960 (nod) | 0 / 0 | PASS |
| [female-hair-sidepart.glb](../female-hair-sidepart.glb) · [checks](checks/hair-sidepart/gate.json) | 2,982 | 0.118 | — | 0 | 0 | 0.713 (run) | 0 / 0 | PASS |
| [female-sneakers.glb](../female-sneakers.glb) · [checks](checks/sneakers/gate.json) | 3,492 | 0.174 | — | 0 | 0 | 0.994 (run) | 0 / 0 | PASS |

[GLB format, texture and bind evidence](assets.json). The garment texture payloads are byte-identical to round one.

### Signed distance by clip, mm

| Clip | Samples | T-shirt | Dress | Jeans | Bob | Spiky | Sidepart | Sneakers |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| rest | 1 | 1.871 | 1.519 | 0.952 | 1.500 | 3.233 | 1.059 | 1.951 |
| walk | 142 | 0.598 | 0.573 | 0.713 | 1.387 | 2.070 | 0.917 | 1.328 |
| run | 76 | 0.564 | 0.643 | 0.631 | 1.359 | 2.171 | 0.713 | 0.994 |
| wave | 161 | 1.648 | 1.300 | 0.911 | 1.386 | 2.032 | 1.011 | 1.951 |
| jump | 126 | 1.259 | 1.009 | 0.952 | 1.500 | 2.029 | 1.008 | 1.056 |
| idle | 221 | 1.420 | 1.221 | 0.923 | 1.441 | 2.011 | 1.025 | 1.951 |
| nod | 141 | 1.732 | 1.425 | 1.011 | 1.297 | 1.960 | 0.985 | 1.951 |
| dance | 161 | 0.832 | 0.974 | 0.889 | 1.210 | 1.995 | 0.914 | 1.948 |
| sit_down | 73 | 1.178 | 0.715 | 0.524 | 1.500 | 2.028 | 0.986 | 2.644 |
| sit_idle | 181 | 1.255 | 1.383 | 0.615 | 1.519 | 2.060 | 0.984 | 2.624 |
| stand_up | 61 | 1.279 | 0.794 | 0.531 | 1.500 | 2.029 | 0.973 | 2.351 |
| hold_item | 121 | 1.652 | 1.479 | 0.924 | 1.429 | 2.025 | 1.055 | 1.951 |
| hold_box | 121 | 1.529 | 1.810 | 0.978 | 1.489 | 2.007 | 1.054 | 1.951 |
| hold_bag | 121 | 1.459 | 1.500 | 0.938 | 1.497 | 2.028 | 1.058 | 1.951 |
| take_item | 121 | 1.438 | 1.589 | 0.922 | 1.441 | 2.029 | 1.059 | 1.951 |

Both collision counts are zero for every listed module and clip. All three v2 garments meet the signed-distance requirement.

## Finish and layering

The offset bake used nearest-body directions from signed vertex distances and triangle witnesses across the full pose bank. It projected the penetration plus 1.5 mm target into bind space, clamped the offset to 30 mm and restored constrained components after smoothing. After a crossed edge was subdivided, its material coordinates, tangents and joint influences were interpolated. Weight and fit trials were evaluated against the motion bank. The hem edges were cut in the already-rigged panels and folded inward. The T-shirt cut leaves the waistband in its original position. The jeans retain the lower cut. A localized taper gives the opposite female sneaker room when the feet cross in the running clip.

| Garment | Crossed edges split | Turned hem segments | Bind hem height mm | Peak bake offset mm | Peak reimport adjustment mm | Evidence |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| tshirt | 51 | 127 | 430.000 | 30.000 | 10.000 | [trace](female-tshirt-v2.fit.json) |
| dress | 0 | 0 | — | 4.628 | 0.750 | [trace](female-dress-v2.fit.json) |
| jeans | 0 | 100 | 134.000 | 0.000 | 8.500 | [trace](female-jeans-v2.fit.json) |

[Full layering measurements](layering.json). Every sampled pair count is zero. The smallest cuff-to-collar gap along the posed shin axis was 7.928 mm. Positive values put the cuff above the collar in that projection.

| Clip | T-shirt / jeans pairs | Jeans / sneakers pairs | Dress / sneakers pairs | Left cuff gap mm | Right cuff gap mm |
| --- | ---: | ---: | ---: | ---: | ---: |
| rest | 0 | 0 | 0 | 15.481 | 15.544 |
| walk | 0 | 0 | 0 | 12.172 | 11.640 |
| run | 0 | 0 | 0 | 8.708 | 7.928 |
| wave | 0 | 0 | 0 | 15.481 | 15.544 |
| jump | 0 | 0 | 0 | 10.934 | 11.189 |
| idle | 0 | 0 | 0 | 15.481 | 15.544 |
| nod | 0 | 0 | 0 | 15.481 | 15.544 |
| dance | 0 | 0 | 0 | 13.172 | 13.238 |
| sit_down | 0 | 0 | 0 | 22.089 | 22.769 |
| sit_idle | 0 | 0 | 0 | 21.575 | 22.515 |
| stand_up | 0 | 0 | 0 | 21.575 | 22.515 |
| hold_item | 0 | 0 | 0 | 15.481 | 15.544 |
| hold_box | 0 | 0 | 0 | 15.481 | 15.544 |
| hold_bag | 0 | 0 | 0 | 15.481 | 15.544 |
| take_item | 0 | 0 | 0 | 15.481 | 15.544 |

## Renders

- Six reimported Cycles CPU views per garment. [T-shirt](renders/tshirt/views.json) · [Dress](renders/dress/views.json) · [Jeans](renders/jeans/views.json)
- [Full outfits sheet](renders/full-outfits.png). Rows show bob with T-shirt and jeans, bob with dress, and spiky with T-shirt and jeans. All wear the female sneakers. The outfit captures use idle frame 18.

### Independent visual review

The final sheet shows the requested bob casual, bob dress and spiky casual outfits at idle frame 18. The T-shirt hem stands apart from the jeans waistband. A narrow band of skin separates each denim cuff from its sneaker opening. Both layering checks pass in the rendered front, oblique, side and rear views.

The jeans now end at calf length. The cuffs look level from the front and back. Side and oblique views show mild fabric puckering and a slight cuff-edge ripple. A small rear waistband lip remains in the isolated side views. The T-shirt retains the purple controller graphic and straight hem. Dark folds below the sleeve openings remain visible in the front-left and profile rest views. The dress silhouette reads cleanly.

The reviewed exports match T-shirt `4ef70a987bf59e128616e0577207e2e4ba0d845a6a646711d928be02f72e641d`, dress `df3dfee402b00b18c0add83a30d31ed20b81714dc2c60e3dcab91a025a9b0296`, jeans `0f466e9fc3af0e31e0c25a1faec7d03184c3fbdf77171e53bef625a6756197f4` and sheet `9f59136f7c8b791e228de2aeeea0ecdde267861a3a40270e511bbbd29c8aa9eb`. The PNG hashes matched the review manifests.

## Recheck

Run from this directory. The Blender wrapper sets two threads and uses the provided local Blender executable.

```sh
./run_blender.sh verify.py
./run_blender.sh verify.py -- --layers
node validate_assets.cjs
./run_blender.sh render_final.py -- tshirt dress jeans outfits
```

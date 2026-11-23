# Escalator passenger journey

The original GJH mall visitor travels between two 2 m floor slabs in **26.2392574 s**, rising 3 m on the original escalator. In the mall module preview, select **Escalator landings**, then **Travel between floors**. Pause or drag the position slider to inspect a handoff. **Ride a step** plays the separate 17.8 s study, starting and ending with both feet on the same moving tread. [Module preview](../../../mall-modules-preview/) · [Standing ride measurements](README.md)

| Preview time (s) | Native machine time (s) | Shoe support |
| --- | --- | --- |
| 0–2.734 | −3.534 to −0.800 | Walk from the lower slab across its 120 mm floor joint to the fixed lower deck. |
| 2.734–4.734 | −0.800 to 1.200 | Plant the leading shoe on moving tread `STEP_00`, then bring the trailing shoe aboard. |
| 4.734–20.904 | 1.200 to 17.370 | Stand on the same tread through the incline and onto the upper flat. |
| 20.904–22.694 | 17.370 to 19.160 | Plant the leading shoe on the upper deck while the trailing shoe still rides the tread, then bring it across. |
| 22.694–26.239 | 19.160 to 22.705 | Walk across the upper 120 mm floor joint and stop with both feet on the upper slab. |

Translating the original walk cycle across the combs produced unsupported poses and sliding shoes. The journey keeps the original meshes and limb lengths. During each transfer, a two-joint solve rotates the hips and knees to keep a planted shoe fixed relative to its current support while the other shoe swings. The standing phase uses the native idle pose and tread motion. [Native gait comparison](transfers.md)

The full-route regression probes the actual shoe and surface geometry at 120 Hz, with extra samples at phase boundaries and the endpoint. All **3,162 poses** retained foot support, with **5,367 planted contacts**. The largest change between successive planted measurements on the same surface was about **9.32 nm**. Maximum measured sole penetration was **0.088 µm**. These are numerical results for the centred, fixed route.

An independent check followed both shoe meshes through 1,576 poses. At each terminal it found a 302.56 mm shoe spanning the slab, joint and deck while planted on the 120 mm profile. Removing the profile leaves that sole contact unsupported. Sampled clearances between the swinging shoe underside and the actual comb teeth reached a minimum of 26.67 mm at the lower comb and 51.80 mm at the upper comb.

Pause at **3.73 s** to see the leading shoe on the moving tread and the trailing shoe on the lower landing. At **21.80 s** the leading shoe is on the upper landing and the other is still on the tread. With the position slider focused, the arrow keys move by 0.01 s. These visual and geometric checks cover one guided ascent of the unscaled visitor.

Run both checks from the repository root with the project dependencies installed.

```sh
node --test tests/mall-escalator-passenger*.test.mjs tests/mall-escalator-route-contact.test.mjs
```

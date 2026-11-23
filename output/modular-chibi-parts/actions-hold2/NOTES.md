# Modular chibi carry and shelf actions

[hold_actions.glb](hold_actions.glb) contains three 2.0 s loops for the demo body. Each clip has 49 samples from frame 0 through 48 at 24 fps, one quaternion rotation track for each of the 65 original joints, and zero translation or scale tracks. The demo body measured 999.512 mm tall and 9,512 triangles. The exported parent links match the demo skeleton. The largest world bind-matrix component difference was 0.00000120. [Readback and gate results](checks/summary.json)

| Clip | Prop | Motion | Cycles views |
| --- | --- | --- | --- |
| hold_box | [Kraft parcel](props/box.glb), 292 triangles | Both hands support the lower side edges of a 304 × 219.1 × 216.8 mm parcel. The thumbs brace the walls, the fingers curl beneath the base, and the load rises and falls through 8.0 mm. The minimum head-to-box surface gap was 16.853 mm. | [Front and side at frames 0, 12, 24, 36](renders/hold_box.png) |
| hold_bag | [Paper shopping bag](props/bag.glb), 948 triangles | The right hand hooks the padded inner handle. The outer cord hangs lower. Wrist rotation produces a rigid swing of −4.5° to +4.5° and 14.0 mm of fore-and-aft travel at the attachment origin. | [Front and side at frames 0, 12, 24, 36](renders/hold_bag.png) |
| take_item | [Jam jar and display shelf](props/shelf_item.glb), 700 + 360 triangles | The hand reaches the stationary sample at frame 29, lifts it 23.84 mm, and draws it 98.0 mm toward the chest by frame 48. The display remains upright. | [Front and side at frames 0, 16, 29, 39](renders/take_item.png) |

The individual PNGs are in [renders/](renders/). The previews show the exported assets with the bob and v3 sneakers. All prop materials use flat colours. The animation build reuses the Astra skeleton I/O, the fitted grip from its hold_item clip and the supplied relaxed hand poses. The parcel uses individually authored finger rotations on both hands. Each action contains its own finger keys.

## Attachments and playback

Instantiate the prop GLB once. Apply the named node's transform at unit scale after evaluating the skeleton. Both continuous carries use a single rigid parent, including the two-handed box. Its left hand follows the baked support position. All three parents are `mixamorig:RightHand`.

| Node | glTF joint-local translation in metres | glTF quaternion XYZW | Full precision and Blender bone-head equivalent |
| --- | --- | --- | --- |
| Parcel | (0.18204346, 0.11279181, 0.10142164) | (−0.86549461, −0.11057544, −0.44077593, 0.21073377) | [box.attachment.json](props/box.attachment.json) |
| Market bag | (0.02593105, 0.02887661, 0.03611930) | (−0.83508277, 0.24741291, −0.34302348, 0.35179326) | [bag.attachment.json](props/bag.attachment.json) |
| Jam jar | (0.02593103, 0.02887667, 0.03611938) | (−0.30049536, 0.01249045, −0.44810084, 0.84187424) | [shelf_item.attachment.json](props/shelf_item.attachment.json) |

Compose the glTF joint world matrix with the supplied joint-local transform. In Blender, compose the armature world matrix, the pose-bone matrix and the supplied Blender transform in that order. These values are relative to the bone head. Replace the moving node's imported translation and rotation when attaching it. The shelf-item GLB stores the jar's initial position on the deck. Comparing actual prop vertices reconstructed from raw glTF channels against the Blender replay gave a maximum difference of 0.000561 mm over all sampled times.

### Shelf pickup and repeat

1. On the first play, leave **Jam jar** at its imported pickup stop throughout the reach. **Display rail** remains stationary.
2. At **frame 29**, 1.2083 s, attach the jar to the right hand. Keep it attached through **frame 48**, 2.0 s. The measured transform change at handoff was under 0.00054 mm.
3. At the start of a repeat, release the jar at the chest-side return stop. It rests there through frame 3. Slide it along the shelf to the pickup stop between frames 3 and 16 using smoothstep, then hold it there until frame 29. This gives repeated takes a continuous prop path. A single play can end with the jar in the hand.

Both stops, the static shelf transform and the attach event are included in the shelf attachment JSON. The initial pickup and the continuous repeat were both collision-tested. The worst prop loop seam was 0.000287 mm across the three clips.

### Ground placement

The barefoot animation uses world floor zero. The v3 sneaker tread reaches 6.00011 mm below the barefoot sole at bind. When equipping those sneakers, raise the character root **6.0002 mm**. Apply the same lift to the two free jar positions. Scale only the static shelf vertically about its floor origin by `1 + lift / shelf_deck_z_m`. This keeps the pedestal on the floor and its deck under the jar. The Blender preview applies this configuration directly. [Machine-readable placement](placement.json) · [Shod replay](grounded.py)

## Acceptance measurements

Each clip was reimported and evaluated at 49 integer frames and 48 half frames on each body. The grip numbers below are the **largest** sampled distance from the closest finger-skin vertex to a prop surface during the grip. These witnesses give a conservative upper bound on the nearest surface distance. For take_item the grip interval begins at frame 29. Each box value identifies a separate supporting hand.

| Clip | Target self-overlap pairs, demo / master | Maximum grip gap, demo | Maximum grip gap, master | Prop/body pairs, both bodies | Maximum prop penetration | Sole drift, barefoot and shod |
| --- | ---: | --- | --- | ---: | ---: | ---: |
| hold_box | 0 / 0 | L 0.9254 mm, R 1.3961 mm | L 1.0203 mm, R 1.8724 mm | 0 | 0 mm | 0 mm |
| hold_bag | 0 / 0 | R 1.2458 mm | R 1.9520 mm | 0 | 0 mm | 0 mm |
| take_item | 0 / 0 | R 1.1041 mm | R 2.3194 mm | 0 | 0 mm | 0 mm |

The table rounds grip upper bounds upward. All heel and forefoot support patches stayed within 0.00018 mm of the floor. The lowest barefoot sample was −0.0000015 mm on the master. The grounded sneaker tread stayed at or above +0.000062 mm, with zero measured sole drift. The body loop seam was below 0.00027 mm across both rigs. [Per-frame CSVs](checks/) · [Grounded measurements](checks/grounded.json)

- Body self-overlap uses the supplied bodycheck.Checker on evaluated triangles, its exact-rest-position seam rule, and the arm_contact and knee_contact classifiers from body-fix. Across the three clips, the peak whole-mesh counts including other regions were 440, 318 and 418 on the demo and 362, 442 and 540 on the master, in the order shown above. The CSVs retain these counts alongside the target counts.
- Prop penetration uses whole-body versus whole-prop triangle intersections and a bidirectional test for fully enclosed connected shells. The containment test uses a component's bounds and oriented solid angle. Both counts were zero, including the shelf and each disconnected part. A separate shod assembly replay also checked the shelf and carried props against the sneakers.
- The lower-head measurement uses vertex-to-face and edge-to-edge witnesses from the existing hand surface checker. The 3 mm grip gate uses actual finger-skin witnesses on each required hand.

### Hair and sneakers

The supplied vertex and triangle checkers evaluated each module on the master at the same 97 times per clip. **All twelve clip/module combinations returned 0 inside vertices and 0 intersecting triangle pairs.** The table gives the minimum signed vertex clearance in mm.

| Clip | [Bob v2](checks/bob/) | [Spiky v1](checks/spiky/) | [Side-part v3](checks/sidepart/) | [Sneaker v3](checks/sneakers/) |
| --- | ---: | ---: | ---: | ---: |
| hold_box | 5.818 | 5.208 | 0.993 | 3.627 |
| hold_bag | 4.891 | 5.211 | 0.994 | 3.627 |
| take_item | 4.891 | 5.212 | 0.994 | 3.627 |

The adapter reads the original body-fix/act checker, selects the three new names through its additional-actions argument and sets its clock to 24 fps with half-frame samples. It preserves both upstream geometry tests. The corrected shared motion GLB is supplied as the existing-motion argument. [Checker adapter](module_checks.py)

Khronos glTF Validator 2.0.0-dev.3.10 returned **0 errors and 0 warnings** on each of the four GLBs. It emitted one informational unused-skin message for the meshless animation bank. The prop triangle counts include all mesh nodes, decorations and materials in each file. [Validator reports](checks/khronos.json)

## Exact reproduction commands

Run in the supplied checkout. The wrapper starts the specified guarded Blender 5.1.2 in background mode and places its temporary resources under this directory. Animation, modelling, geometry checks and Cycles CPU rendering run in Blender. The Khronos command uses the validator already installed in the checkout.

~~~sh
cd /Users/yapweijun/Documents/GitHub/Blender-3D-Gallery/output/modular-chibi-parts/actions-hold2
sh run.sh build.py
sh run.sh props.py
sh run.sh audit.py
sh run.sh module_checks.py
sh run.sh grounded.py
node validate_glbs.cjs
sh run.sh verify.py
sh run.sh render.py
~~~

The summary includes hashes of the delivered assets and the body, gestures, Astra actions, corrected motion, master and four modules used for verification. Rebuilding the bank and all three props reproduced their SHA-256 hashes. [Inputs, outputs and gate status](checks/summary.json)

## What remains

All requested asset gates passed. A consuming player must apply the sockets, shelf event and footwear placement. Gallery integration and browser playback were outside this Blender-only delivery.

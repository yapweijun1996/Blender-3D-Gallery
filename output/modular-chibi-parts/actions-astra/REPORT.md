# Modular chibi chair and cup actions

The four clips in [actions.glb](actions.glb) play on the round-two body. Place the chair and character armature at the same world origin, with unit scale and the same heading. The chair faces Blender −Y. Its origin is on the floor directly below the centre of its seat. The Hips animation places the character in front of the chair and moves it onto the cushion.

**Proportion trade-off.** With the original shin length, planted heels and forefeet, vertical shins and the authored near-horizontal thigh angle, the support surface under this body measures 159.0 mm above the floor. The chair has a 252.0 mm seat. The three chair clips use a fixed 1.43459× local longitudinal scale on each shin and keyed knee/ankle translations. This makes their standing endpoint 1,098.265 mm tall. The source body and the hold endpoint measure 999.512 mm. Switching directly between the two standing poses changes the silhouette by 98.753 mm. Runtime playback needs to retain the scale and translation tracks. The three chair clips join continuously.

## Files and clip inventory

| File | Export readback |
| --- | --- |
| [actions.glb](actions.glb) | 66 nodes, 65 named joints, 0 meshes, 4 animations |
| [chair.glb](chair.glb) | 1 mesh, 1,052 triangles, 4 flat-colour materials, 328 × 212 mm cushion, seat height 0.2521 × rest-body height |
| [prop.glb](prop.glb) | 1 mesh, 572 triangles, 4 flat-colour materials. Open ceramic cup, 94 mm tall, 40 mm grip diameter, 45.2 mm maximum rim diameter |
| [attachment.json](attachment.json) | Right-hand offsets and rotations for the Blender pose-bone head and the glTF joint |

Each clip starts at 0 s. The glTF contains 65 quaternion rotation channels, 5 translation channels and 2 scale channels in each clip. The translation channels address Hips, both lower legs and both feet. The scale channels address the lower legs. The hand-holding action uses unit shin scale. Sample counts include both endpoints at 30 fps.

| Clip | Duration | Samples | Playback | Reviewed front and side views |
| --- | ---: | ---: | --- | --- |
| sit_down | 1.2 s | 37 | Once | [0, 12, 24, 36](renders/sit_down.png) |
| sit_idle | 3.0 s | 91 | Repeat | [0, 22, 45, 68](renders/sit_idle.png) |
| stand_up | 1.0 s | 31 | Once | [0, 10, 20, 30](renders/stand_up.png) |
| hold_item | 2.0 s | 61 | Repeat | [0, 15, 30, 45](renders/hold_item.png) |

The seated torso uses the opening posture of the supplied Studio sit.001 clip. The existing idle supplies the standing arm pose. The hip path, foot planting and chair transitions were authored for this chair. Hips travels 139.188 mm backward and 120.995 mm down during sit_down. The head and upper spine move independently during the seated breath. The top of the body moves through a 3.284 mm vertical range over that loop.

## Body, chair and floor

The body GLB reimported with 6,010 vertices and 9,512 triangles. Every authored frame used the evaluated body mesh. The chair test welded export seams for component identification, tested the nine closed solids individually, measured inward depth, and checked all chair triangles against the body triangles. The floor test included every body vertex. Sole drift tracks the same 15 left and 16 right sole vertices relative to the beginning of the chair sequence.

| Clip | Frames | Maximum vertices inside chair, any depth / over 2 mm | Deepest entry | Maximum triangle pairs | Minimum body Z | Maximum sole XY drift |
| --- | ---: | --- | ---: | ---: | ---: | ---: |
| sit_down | 37 | 0 / 0 | 0 mm | 0 | −0.000315 mm | 0.000304 mm |
| sit_idle | 91 | 0 / 0 | 0 mm | 0 | −0.000313 mm | 0.000260 mm |
| stand_up | 31 | 0 / 0 | 0 mm | 0 | −0.000306 mm | 0.000328 mm |
| hold_item | 61 | Cup in scene | — | 0 cup/body | −0.000150 mm | 0 mm |

There were **0 vertices below −1 mm** across all 220 frames. On every seated frame, the heel and forefoot of each foot reached the floor within 0.001 mm. The left and right thighs were 7.985° and 7.869° from horizontal. Both shins were within 0.00004° of vertical. The lowest left and right pelvis/proximal-thigh vertices above the cushion were 0.358 and 0.201 mm from its top. Each side had three support vertices within 2 mm.

A further 156 halfway samples tested continuous Blender playback between authored chair frames. Maximum chair/body triangle overlap was 0. The minimum body heights in sit_down, sit_idle and stand_up were −0.05077, −0.00031 and −0.07307 mm. The corresponding maximum sole drifts were 0.04610, 0.00025 and 0.06631 mm. The largest mesh displacement across a chair-clip join or either loop seam was 0.000185 mm.

The [full audit](checks/actions.json) includes readback, ranges, join errors and halfway samples. Per-frame measurements are available for [sit_down](checks/sit_down.csv), [sit_idle](checks/sit_idle.csv), [stand_up](checks/stand_up.csv) and [hold_item](checks/hold_item.csv).

## Right-hand grip

Attach the cup root below mixamorig:RightHand. In glTF joint-local coordinates its translation in metres is (0.02593084, 0.02887651, 0.03611905). Its rotation quaternion in XYZW order is (0.27544212, 0.76551259, −0.46392176, 0.35056925). Use unit scale. The parent joint world matrix multiplied by this local transform places the upright cup inside the fingers. Blender's bone-parenting UI uses a tail offset. The Blender values in the attachment file are relative to the pose-bone **head** and can be multiplied directly by its pose matrix.

Over all 61 frames, the nearest cup surface lay 0.36500–0.36511 mm from the thumb pad and 0.27109–0.27121 mm from the index pad. The measurement uses the original hand library's fixed pulp triangle patches and checks vertex/face and edge/edge witnesses. Cup/body triangle-overlap pairs were 0. The elbow flexed 101.4425° and the cup centre stayed 552.902–555.507 mm above the floor. All 20 right finger channels matched the source grip_small action within 0.00000080 per quaternion component, allowing equivalent quaternion signs. The glTF attachment and the independent Blender replay agreed within 0.00042 mm at the cup origin, rim height and barrel radius. [Grip close-up](renders/cup_detail.png)

All 65 joint names and parent links matched the round-two body. The maximum local bind-matrix component difference on GLB readback was 0.00000220. The maximum rotation-quaternion length error was 0.00000012.

## Garment checkers

Both checkers used the older rigged master, the exact specified module GLBs, the exported clips and their Blender 5 action slots. Counts are the worst per-frame result over 91 sit_idle samples and 61 hold_item samples for each module.

| Module | Pose | Inside vertices | Triangle-overlap pairs | Minimum signed body clearance |
| --- | --- | ---: | ---: | ---: |
| Bob v2 | Rest | 0 | 0 | 5.818 mm |
| Bob v2 | sit_idle | 0 | 0 | 4.892 mm |
| Bob v2 | hold_item | 0 | 0 | 4.889 mm |
| Sneakers v2 | Rest | 0 | 0 | 0.537 mm |
| Sneakers v2 | sit_idle | 0 | 0 | 0.667 mm |
| Sneakers v2 | hold_item | 0 | 0 | 0.537 mm |

The seated sneaker sole reaches 0.777 mm below the barefoot floor plane. Its lowest hold_item point is within 0.001 mm of that plane. The garment/body results and every tested frame are in [hair checks](checks/hair/) and [shoe checks](checks/shoes/).

## Visual review and scope

The front and right-side Cycles renders show four timestamps of each clip, 32 views in total. In profile, the character leans forward during the transfer, lands on the front half of the cushion, and keeps both soles down. The seated back stays clear of the backrest. The two idle poses have subtle head and chest motion. In the grip close-up the fingers wrap the cup and the flared rim clears the index finger. The chair stance has visibly longer calves than the holding stance. The review covers these Blender exports and the two specified modules. The optional walking carry was omitted.

## Reproduce locally

Run from this directory. The wrapper uses the supplied guarded Blender 5.1.2 executable and keeps temporary resources inside this directory. Source assets are read-only.

~~~sh
./run_blender.sh build_props.py
./run_blender.sh build_actions.py
./run_blender.sh validate_actions.py
./run_blender.sh render_actions.py

master_blend="$PWD/../master/GJH_Chibi_Master_rigged.blend"
for checker in motion_check.py motion_check_tri.py; do
  ./run_blender.sh "$checker" "$master_blend" "$PWD/actions.glb" \
    "$PWD/../hair-fit-astra/round2/hair_bob_v2.glb" "$PWD/checks/hair"
  ./run_blender.sh "$checker" "$master_blend" "$PWD/actions.glb" \
    "$PWD/../shoes-sol/round2/shoes_sneaker_v2.glb" "$PWD/checks/shoes"
done
~~~

Passing the original motion.glb as the second checker argument also checks its legacy clips and reads sit_idle and hold_item from the local actions.glb.

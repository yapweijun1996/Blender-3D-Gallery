# Authored action body clearance

**Partial result.** Reimporting [actions_fixed.glb](actions_fixed.glb) clears all 20,930 sampled arm, hand and finger contacts against the master torso, head and legs. The hold_item clip passes the requested target gate. The three chair clips retain 3,116 same-side shin/thigh pair occurrences. The strict four-clip gate therefore fails. The maximum target residual is 4.141088 mm on the left knee at sit_down 35.5. Garment clearance was outside this body-only measurement.

## Collision results

Blender 5.1.2 sampled 220 integer frames and the 216 intervening half frames at 30 fps. Each cell counts unordered non-adjacent triangle pairs summed over the indicated sample times. The same pair may recur at different times.

| Clip | Samples | Integer target before → after | Half-frame target before → after | Combined before → after | Deepest target after | Deepest whole-body pair after |
| --- | ---: | ---: | ---: | ---: | --- | --- |
| sit_down | 73 | 1,908 → 111 | 1,816 → 109 | 3,724 → 220 | 4.141088 mm, left knee, 35.5 | 7.317939 mm, right thigh internal, 16.5 |
| sit_idle | 181 | 4,191 → 1,365 | 4,145 → 1,350 | 8,336 → 2,715 | 4.100275 mm, left knee, 0 | 5.701645 mm, head internal, 71 |
| stand_up | 61 | 1,511 → 95 | 1,403 → 86 | 2,914 → 181 | 4.133855 mm, left knee, 0.5 | 7.352081 mm, left thigh internal, 16.5 |
| hold_item | 121 | 4,570 → 0 | 4,502 → 0 | 9,072 → 0 | 0 mm | 8.583875 mm, right forearm/upper arm, 56 |
| **Total** | **436** | **12,180 → 1,571** | **11,866 → 1,545** | **24,046 → 3,116** | **4.141088 mm** | **8.583875 mm** |

The original hold_item frame 44 reproduces 46 left forearm pairs, comprising 42 against LeftUpLeg and four against Spine1 under the shared checker's summed-weight labels. The corrected sample has zero target pairs. Both reports include every target pair's master triangle IDs, per-region totals, whole-body counts and the deepest pair at every timestamp. [Before](body_selfcheck_before.json) · [After](body_selfcheck_after.json)

## Body, props and motion

- The audit opens GJH_Chibi_Master_rigged.blend and binds each imported action and its Blender 5 action slot to the original master armature. The mesh has 5,160 vertices and 8,006 triangles. The shared body checker uses an epsilon-zero BVH in evaluated world space. It excludes triangles sharing an exact rest-position vertex, including UV splits with identical weights. The target labels and triangle SAT separation depths follow the seven-clip checker. Depth measures the separating translation of the individual triangle pair.
- The pose search opens each upper arm about a lateral clearance axis. The forearm counterrotation carries the palm's original orientation through that adjustment. The search measures the master triangles, adds an angular margin, smooths the correction over neighboring keys and matches the chair transition endpoints. The largest upper-arm adjustments are 16.9° on the left and 18.9° on the right.
- The GLB has 66 nodes, 65 joint names, the four original clip names and durations, and 72 original channel targets per clip. The GLB header and JSON chunk are byte-identical. All binary differences occur in the existing LeftArm, LeftForeArm, RightArm and RightForeArm quaternion outputs. This preserves all time inputs, Hips/lower-leg/foot translations, lower-leg scales, hand and finger channels and inverse bind matrices. The output is 333,360 bytes. Reimport reproduced the intended posed vertices to within 0.000306 mm. [Bake readback](bake_verification.json) · [Binary and motion audit](verification.json)
- Across all 436 samples, the before/after change in minimum foot height, sole-vertex XY and Hips position was 0 mm. Absolute sole drift from the source starting pose peaked at 0.066285 mm in stand_up. The seat-support gaps matched the source, including 0.358224 mm on the left and 0.200570 mm on the right at sit_idle frame 0. The maximum full-mesh endpoint difference at the three chair joins and two loop seams was 0.000256 mm.
- All 315 seated-sequence samples had zero body vertices inside the chair's nine solids, zero chair/body triangle pairs and zero chair vertices enclosed by the body. For the reciprocal test, each connected chair solid has a path to the exterior and no intersection with the body surface.
- The cup had zero body triangle pairs at all 121 hold_item samples on both the requested master and the original cup-grip body. On the authored grip body, the corrected thumb gap is 0.36499–0.36510 mm and the index gap is 0.27104–0.27122 mm. The largest matched-frame change is 0.00012 mm. The earlier master has a different hand mesh and hand pose. Its original thumb and index gaps are about 61.42 and 33.24 mm with the supplied attachment. Their matched-frame change is at most 0.00018 mm. The comparison uses fixed pulp triangle patches and includes vertex/face and edge/edge closest points. Use the original [attachment.json](../actions-astra/attachment.json).

## Remaining knee folds

At the common seated pose, seven left and eight right pairs lie in the posterior knee crease. The seven-clip repair used joint translation and segment compression in deep flexion. The authored clips already have fitted translation and shin-scale tracks that this task requires preserving.

The rotation search covered thigh and shin axial turns, knee-plane swivel, pelvis pitch, foot and toe counterrotation, and constrained fits to the sole and cushion. No tested rotation-only correction cleared both knees while preserving planting, seat support and the chair. Two reproducible Blender trials illustrate the conflict at sit_idle 0.

| Trial | Left/right knee pairs | Max sole XY change | Left/right gap over the seat |
| --- | --- | ---: | --- |
| Source | 7 / 8 | 0 mm | 0.358 / 0.201 mm |
| Extend both knees 15° | 0 / 0 | 81.135 mm | 0.358 / 0.201 mm |
| Alternate pelvis orientation with original shins and feet | 0 / 0 | 0.000170 mm | 40.193 / 39.779 mm |

The second trial preserved the numerical Hips height while visibly separating the support surface from the cushion. Both trials were excluded from the delivery. These results describe the tested solutions. [Measured knee trials](knee_trials.json)

## Visual comparison

Each plate shows four matched poses before and after, with the same camera, scale, props and attachment. Sit-down and stand-up retain the forward transfer and planted feet. The seated hands approach the thighs with additional lateral arm clearance. The extra hold_item plate shows the grip on its authored hand geometry. [Sit down](renders/sit_down_before_after.png) · [Seated idle](renders/sit_idle_before_after.png) · [Stand up](renders/stand_up_before_after.png) · [Hold item on master](renders/hold_item_before_after.png) · [Hold item on authored grip body](renders/hold_item_authored_grip_before_after.png)

## Exact reproduction

Use the specified macOS Blender bundle and guard library. The wrapper locates those paths, sets a temporary directory within this output folder, disables automatic script execution and runs the Python entry points inside Blender. Rendering uses Cycles CPU. Source inputs and the shared measurement, importer and hand-contact helpers are read from their original directories.

```sh
cd /Users/yapweijun/Documents/GitHub/Blender-3D-Gallery/output/modular-chibi-parts/actions-fix
sh run.sh audit.py -- before
sh run.sh arms.py
sh run.sh bake_actions.py
sh run.sh audit.py -- after
sh run.sh knee_trials.py
sh run.sh render_pairs.py
sh run.sh verify.py
```

The last command writes verification.json and exits with status 2 because target_zero_every_sample is false. The other five gates pass.

| Input or output | SHA-256 |
| --- | --- |
| Master .blend | 0339318b375836ab8891e49bda178da7e6f115e012e83385d9f8850949a7bd6f |
| Source actions.glb | e0b71ba549ed60f15a23b925be39cdf0eeef1ba9185fef35572cef8117b984d9 |
| Supplier attachment.json | 404c05669491a8ebe8d9e44659f0469af57278a64159e5fbf572f525877de3 |
| Corrected actions_fixed.glb | 0d3a57ae8906edeebee590b67d0e84333640389340bfbfbe0af041ccf8f871c9 |

# Chibi master body clearance

[motion_fixed.glb](motion_fixed.glb) removes all 30,899 sampled arm-to-body and same-side shin-to-thigh intersections across the seven shared actions on the supplied master. A fresh Blender import found zero in these regions at all 415 integer frames and all 408 intervening half frames. The master still has 148,758 non-adjacent triangle-pair occurrences across the integer frames. Every occurrence is recorded in the [after report](body_selfcheck_after.json).

## Results on the delivered GLB

Totals count each unordered triangle pair once per frame. “Target” includes an arm, hand or finger against the torso, head or lower body, and a shin against its same-side thigh. “Peak” is the largest whole-body count in a single frame. The deepest residual uses the pair depth defined below.

| Clip | Inclusive frames at 24 fps | All before | All after | Peak before → after | Target before → after | Deepest residual in mm | Frame and region |
| --- | --- | ---: | ---: | --- | --- | ---: | --- |
| walk | 1–57 | 38,958 | 28,651 | 786 → 521 | 9,847 → 0 | 6.255094 | 52 · RightUpLeg / RightUpLeg |
| run | 0–30 | 20,512 | 17,166 | 851 → 573 | 2,721 → 0 | 7.011538 | 24 · LeftUpLeg / LeftUpLeg |
| wave | 0–64 | 25,877 | 20,540 | 406 → 317 | 4,908 → 0 | 5.753652 | 58 · Head / Head |
| jump | 0–50 | 18,727 | 16,201 | 434 → 322 | 2,179 → 0 | 6.033794 | 9 · LeftUpLeg / LeftUpLeg |
| idle | 0–88 | 36,079 | 28,131 | 407 → 317 | 6,713 → 0 | 5.753972 | 82 · Head / Head |
| nod | 0–56 | 23,063 | 17,994 | 406 → 317 | 4,319 → 0 | 5.758090 | 43 · Head / Head |
| dance | 0–64 | 20,446 | 20,075 | 325 → 313 | 212 → 0 | 5.755444 | 1 · Head / Head |
| **Total** | **415 frames** | **183,662** | **148,758** | **851 → 573** | **30,899 → 0** | **7.011538** | **run 24** |

The per-side minimum foot height changed by at most **0.004276 mm** on integer frames, at run 23 on the left. The largest change including half frames was **0.112118 mm**, at walk 25.5 on the right. The limit was 1 mm. The comparison uses the minimum world Z over 318 left and 330 right mesh vertices whose strongest weight belongs to Foot, ToeBase or Toe_End. [Verification and per-clip breakdown](verification.json)

## Remaining intersections

The neutral master already contains 318 pairs. Of these, 163 lie where the two eye inserts meet the head, 60 are between the modeled shorts and the two separate leg surfaces, and 95 are inside the foot/toe surfaces. These pairs are included in the collision results. The supplied master has 8,006 triangles, 5,160 mesh vertices and 65 bones. The fit used the original mesh throughout.

Walk and run retain 10,944 and 7,099 hand-internal occurrences respectively. Run also retains local wrist, forearm, elbow, ankle and hip folds. For example, Hips / RightUpLeg has two residual pairs on each of frames 11, 12 and 27, with a maximum of 3.126701 mm across those frames. Foot/ankle totals increased by 27 occurrences in run and 10 in jump. The body-only check leaves garment clearance unmeasured. [Full baseline](body_selfcheck_before.json) · [Full residue](body_selfcheck_after.json)

## Measurement and pose changes

- Blender 5.1.2 opens the specified master, imports the motion GLB, binds each action directly to the master armature and assigns its first action slot. The checker uses the evaluated world-space triangles of Base_Body, including eyes, shorts, toes and fingers.
- An epsilon-zero Blender BVH tests triangle intersections. The primary count excludes triangles sharing a surface vertex. The 1,101 exact-position duplicates have identical bone weights, verified before measurement. They represent split vertices for this adjacency test. The JSON also records the strict index-only total and every additional seam-incident pair.
- Each triangle is labeled by the bone with the largest summed weight across its corners. Every frame lists triangle IDs and pair depths in mm. The depth is the shortest rigid translation that separates those two zero-thickness triangles, computed from their two normals and nine edge-cross-edge separating axes. A tangency or coplanar intersection can have depth zero. This is a local, pairwise geometric metric.
- The pose search increases lateral upper-arm clearance only where required. An elbow adjustment then brings the palm toward its original trajectory within the measured clearance. At deep knee bends a distributed glide and uniform segment compression separate the thigh and shin. A final pelvis or elbow adjustment reduces local folds, and foot compensation brings the measured sole height back to the original trajectory. The run correction includes half-frame keys through the fast swing.
- All changes reside in the motion asset. Its seven clip names, timespans, 65 joint names, and 195 channel targets per clip match the input. The original shared GLB geometry, bind matrices, materials, images, root track and hand/finger samplers are preserved. Only selected animation samplers are redirected to the baked poses. Reimport agreed with the intended master vertex positions to within 0.000479 mm. [Changed channels and round-trip error](bake_verification.json)

## Visual comparison

Each plate puts the original and corrected master side by side at the same frame, camera angle and scale. Walk shows opposite stride phases and greater hand clearance beside the shorts. Wave shows the lowered and raised arm. Run shows the deep right-knee bend and the opposite stride phase. [Walk 27 and 42](renders/walk_before_after.png) · [Wave 0 and 19](renders/wave_before_after.png) · [Run 9 and 17](renders/run_before_after.png)

## Exact reproduction commands

Run in the supplied macOS environment. The wrapper selects the specified Blender executable and guard library, sets the temporary directory under this output folder, and uses background mode with six threads. Rendering uses Cycles CPU. The two key tables can be regenerated by the tune and polish commands. All mesh, pose, measurement and image operations run in Blender.

```sh
cd /Users/yapweijun/Documents/GitHub/Blender-3D-Gallery/output/modular-chibi-parts/body-fix
sh run.sh bodycheck.py -- before
sh run.sh tune.py
sh run.sh polish.py
sh run.sh bake.py
sh run.sh bodycheck.py -- after
sh run.sh review.py
sh run.sh render.py
```

The master SHA-256 is `0339318b375836ab8891e49bda178da7e6f115e012e83385d9f8850949a7bd6f`. The input motion SHA-256 is `ffccda1ba2a50eb10948853e03d17f0d095cd9b953d644c03c4fb9cb95529410`. The corrected motion SHA-256 is `3484f5978e94f3e714b320357397d107dd490d56f2eeb64770be292322f9aa2c`.

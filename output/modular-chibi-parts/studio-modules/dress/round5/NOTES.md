# Studio A-line dress · Round 5

## Deliverables

- [Skinned dress GLB](dress_v5.glb) and [editable Blender source](dress_v5.blend).
- [Fitter](fit_dress_r5.py), [contact solve](contact_fit.py), [local polish](polish_contacts.py), and [Blender runner](run_blender.sh).
- [Six-view rest sheet](six_view.png), [sit_idle minimum-clearance pose](sit_idle.png), and [hold_item minimum-clearance pose](hold_item.png).
- [Vertex summary](motion_check.txt), [vertex samples](motion_check.json), [triangle summary](motion_check_tri.txt), and [triangle samples](motion_check_tri.json).
- [Export readback](export_check.json), [Khronos validator](gltf_validator.json), [byte-identical Blender re-export](blend_replay.json), and [render manifest](renders.json).

The GLB has **4,042 triangles**, 2,860 exported vertices, and **2,508,672 bytes**. The .blend has **6,530,367 bytes** and includes the master body as a fitting reference. The GLB has one skinned dress mesh, 65 joints, up to four normalized influences, and zero animations. The three embedded 1024 × 1024 textures and Tripo material match Round 3. The export retains all 2,752 distinct Round 3 UV coordinates and adds 104 interpolated coordinates. The position-welded surface has four boundary loops and zero shared non-manifold edges. Khronos glTF Validator 2.0.0-dev.3.10 reports zero errors and zero warnings.

Rest clearance is 2.037–29.474 mm at exported vertices and 1.188–29.527 mm at 16,168 face-centre and edge-midpoint probes. Zero of those samples exceed 30 mm.

GLB SHA-256 `0efaca0036372ec5a5acd8d4b26704cdb2973c4cec4bd13304535c5cd2ce6b7b`.

## Fitting and reproduction

The fit begins with [Round 3](../round3/dress_v3.glb). On the [corrected action bank](../../../actions-fix/actions_fixed.glb), the prior Round 4 skirt loft had lower seated penetration. Its lower-panel positions and weights were tapered onto the UV-matched Round 3 mesh. The new fit retained the Round 3 collar and cap-sleeve structure and used the authored Round 3 Tripo material. [Seed comparison](seed_comparison.json)

The fitter sampled all half frames against both corrected banks. It transported worst-frame clearance directions back through each vertex's skin transform, baked up to 30 mm of required offset with a 2 mm margin, and used a Laplacian spread with a lower bound on the required normal component. A regularized contact solve adjusted local positions and normalized weights. The final topology splits 99 edges in crossing-triangle neighborhoods. Swept tests guided the final shoulder, armpit and skirt refinements.

Run these commands from this folder with the guarded Blender 5.1.2 binary referenced by the runner.

```sh
sh run_blender.sh build
sh run_blender.sh check verify replay render zones
sh run_blender.sh body-only
```

The fitter uses shared read-only helpers from the earlier dress rounds. The editable source was reopened and re-exported byte for byte. The staged rebuild sequence is provided for reproduction.

## Motion verification

The supplied numerical checker methods reopened the master and reimported the final GLB. They sampled rest and every integer and half frame, including each clip endpoint. The legacy bank is [motion_fixed.glb](../../../body-fix/motion_fixed.glb), and the added bank is [actions_fixed.glb](../../../actions-fix/actions_fixed.glb) at 30 fps. Blender 5 action slots were bound without changing pose-bone rotation modes. Cycles CPU rendered the review plates.

Each count is the maximum at any single pose. Both checkers report the lowest signed garment-vertex distance in each clip.

**Passed.** All 11 clips and rest met the 0.500 mm floor and had zero inside vertices and zero garment/body triangle-overlap pairs over 1,260 sampled poses. The lowest signed distance was 0.510924 mm in walk at frame 14.

### Vertex checker

| Clip | Poses | Peak inside vertices | Min signed (mm) | Min frame |
| --- | ---: | ---: | ---: | ---: |
| rest | 1 | 0 | 2.036591 | 1 |
| walk | 113 | 0 | 0.510924 | 14 |
| run | 61 | 0 | 0.557111 | 10 |
| wave | 129 | 0 | 1.199229 | 48 |
| jump | 101 | 0 | 1.032198 | 7 |
| idle | 177 | 0 | 1.578229 | 30 |
| nod | 113 | 0 | 1.863014 | 17 |
| dance | 129 | 0 | 1.237360 | 48.5 |
| sit_down | 73 | 0 | 0.564865 | 5 |
| sit_idle | 181 | 0 | 0.596296 | 12 |
| stand_up | 61 | 0 | 0.700883 | 20.5 |
| hold_item | 121 | 0 | 0.597123 | 41 |

### Triangle-overlap checker

| Clip | Poses | Peak garment/body pairs | Min signed (mm) | Min frame |
| --- | ---: | ---: | ---: | ---: |
| rest | 1 | 0 | 2.036591 | 1 |
| walk | 113 | 0 | 0.510924 | 14 |
| run | 61 | 0 | 0.557111 | 10 |
| wave | 129 | 0 | 1.199229 | 48 |
| jump | 101 | 0 | 1.032198 | 7 |
| idle | 177 | 0 | 1.578229 | 30 |
| nod | 113 | 0 | 1.863014 | 17 |
| dance | 129 | 0 | 1.237360 | 48.5 |
| sit_down | 73 | 0 | 0.564865 | 5 |
| sit_idle | 181 | 0 | 0.596296 | 12 |
| stand_up | 61 | 0 | 0.700883 | 20.5 |
| hold_item | 121 | 0 | 0.597123 | 41 |

### Master-body self-contact

The exact master and bank hashes match the prior Blender self-checks. The table lists the overall master-only baseline and the seated thigh/shin subset. Knee depths are the least separating translation for the intersecting triangles. [Body-only evidence](body_only.json)

| Clip | Peak body-only pairs | Peak knee pairs | Deepest knee pair |
| --- | ---: | ---: | --- |
| rest | 318 | — | — |
| walk | 521 | — | — |
| run | 577 | — | — |
| wave | 317 | — | — |
| jump | 322 | — | — |
| idle | 317 | — | — |
| nod | 317 | — | — |
| dance | 313 | — | — |
| sit_down | 396 | 15 | Left thigh/shin, 4.141 mm at 35.5 |
| sit_idle | 401 | 15 | Left thigh/shin, 4.100 mm at 0 |
| stand_up | 396 | 15 | Left thigh/shin, 4.134 mm at 0.5 |
| hold_item | 460 | 0 | — |

[Remaining garment contacts](failure_zones.json) is empty. The seated master-body knee subset peaks at 15 pairs in each of the three seated clips.

## Render review

The rest sheet shows front, back, left, right, three-quarter, and dress-only views in reading order. The original round neckline, cap sleeves, pastel finish, and A-line silhouette remain visible. The seated plate shows cloth gathering around the outside hip and across the hem. The minimum-clearance plates show sit_idle at frame 12 and hold_item at frame 41.

## Earlier report files

An early checker invocation inherited Round 4's input and destination defaults. It rewrote `round4/motion_check.json`, `round4/motion_check.txt`, `round4/motion_check_tri.json`, and `round4/motion_check_tri.txt` with Round 4 results against the corrected action bank.

The [reproduced Round 4 reports](round4-report-recovery/) use Round 4's original action bank and match the previous byte counts and all tables published in its notes. The recovery copies are under Round 5. The corrected Round 5 invocation passes the input GLB and report destination explicitly.

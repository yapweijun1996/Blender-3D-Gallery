# Plain shorts · Studio round 1

[Download the skinned GLB](shorts_v1.glb) or open the [editable Blender file](shorts_v1.blend). The Blender file contains the packed material, master rig and hidden neutral body reference. The reduced Studio exterior is available as a [working Blender file](shorts_exterior_working.blend).

| Export measurement | Result |
| --- | ---: |
| GLB bytes | 234,172 |
| Blender bytes | 1,141,762 |
| Triangles | 2,780 |
| Exported vertices | 2,421 |
| Position-welded vertices | 1,388 |
| Connected shells | 1 |
| Boundary edges | 0 |
| Non-manifold edges | 0 |
| Rest shorts self-intersection pairs | 0 |
| Master joints in matching order | 65 |
| Maximum normalized influences | 4 |
| Embedded Tripo base-colour JPEG | 512 × 512 |
| Khronos errors / warnings | 0 / 0 |

GLB SHA-256 `94b59b9dd67dcd762937f9bd658145425160a9aa69e6f6bc4ee00560bedf5e6a`. The exported JPEG matches the Studio payload byte for byte. The file combines the Studio exterior UVs with UVs for the new lining and rims, sampled from a tan fabric patch in the same atlas. [Export audit](export_check.json) · [Khronos report](gltf_validator.json) · [Rest audit](rest_check.json)

## Construction

Studio part `tripo_part_5` is the tan shorts under the shirt. Its source exterior contains 169,170 triangles and three boundary loops. Exact position welding restored shared geometry while retaining corner UVs. The working exterior was reduced to 1,130 triangles before cleanup. The cut was aligned at the waist, hip, crotch and hem. The lowest hem stands 49.90 mm above the higher neutral knee. [Source inspection](source_inspection.json)

The master body supplied barycentric weights. Smoothing was strongest through the hips and crotch. Pose-space contacts were transported back through the skin to bake position and weight adjustments into the rest mesh. The rear waist was leveled and lowered slightly, the front thigh panels gained room, and a local left-side correction cleared the moving thumb and upper thigh. Thin lining geometry connects the three openings with waist and hem rims. Local separation resolved rest intersections while changing the exterior by at most 0.500 mm. [Fit history](fit_history.json)

## Motion and clearance

The six supplied checker entry points reimported the final GLB against the corrected banks. The adapter retained their measurement methods, sampled every integer and half frame plus each endpoint, preserved precision, and skipped the Workbench previews. The shared bank ran once per checker type. All fourteen clips passed. The lowest signed distance was 1.1920 mm at frame 1.5 of `stand_up`.

Rest vertex clearance ranged from 3.2480 to 22.9907 mm. The 11,120 additional rest face-centre and edge-midpoint probes ranged from 1.5242 to 22.7357 mm. Maximum inside vertices and maximum shorts-to-body triangle pairs were both zero across the 1,623 tested poses, including rest.

| Clip | Samples | Peak inside vertices | Peak overlap pairs | Min signed (mm) | Frame | Failed poses |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `rest` | 1 | 0 | 0 | 3.2480 | 1 | 0 |
| `walk` | 113 | 0 | 0 | 1.4571 | 14 | 0 |
| `run` | 61 | 0 | 0 | 1.2172 | 12 | 0 |
| `wave` | 129 | 0 | 0 | 1.4224 | 19 | 0 |
| `jump` | 101 | 0 | 0 | 1.2581 | 7 | 0 |
| `idle` | 177 | 0 | 0 | 3.2018 | 22 | 0 |
| `nod` | 113 | 0 | 0 | 3.2480 | 0 | 0 |
| `dance` | 129 | 0 | 0 | 2.5972 | 48 | 0 |
| `sit_down` | 73 | 0 | 0 | 1.2170 | 34 | 0 |
| `sit_idle` | 181 | 0 | 0 | 1.2912 | 61.5 | 0 |
| `stand_up` | 61 | 0 | 0 | 1.1920 | 1.5 | 0 |
| `hold_item` | 121 | 0 | 0 | 3.2298 | 15 | 0 |
| `hold_box` | 121 | 0 | 0 | 3.2602 | 15 | 0 |
| `hold_bag` | 121 | 0 | 0 | 3.2409 | 15 | 0 |
| `take_item` | 121 | 0 | 0 | 3.2321 | 24 | 0 |

[Shared vertex](checks/shared_vertex.json) · [Shared triangle](checks/shared_triangle.json) · [Sit and hold vertex](checks/sit_vertex.json) · [Sit and hold triangle](checks/sit_triangle.json) · [Carry vertex](checks/carry_vertex.json) · [Carry triangle](checks/carry_triangle.json) · [Summary JSON](checks/summary.json)

## Visual review

The final GLB was personally viewed across all six rest angles and the three lowest-clearance action frames. A separate reviewer checked the same captures and reference against the manifest. The tan shorts retain the reference's loose above-knee silhouette and cuffed legs. The bend poses show continuous rims and no visible tears, isolated black slits, body poke-through or obvious texture stretching. Slight facets and source creases remain in the side and rear panels.

The light strip above the waist in bare-master shots is from the master body's own texture. The reference shirt covers that region. Rays from the reviewed views identify the dark patches at the openings as hits on cloth or body, with warm base-color texels under the shadows. [Visual detail audit](render_detail_check.json)

[Six views](six_view.png) · [Run frame 12](run.png) · [Sit idle frame 61.5](sit_idle.png) · [Take item frame 24](take_item.png) · [Render manifest](render_manifest.json)

## Reproduction

Run these commands from this folder using the read-only Studio source, master, clip banks and supplied checkers referenced by the scripts. The guarded Blender 5.1.2 runner and Cycles CPU use two threads.

```sh
sh run_blender.sh fit_shorts.py -- --stage
sh run_blender.sh fit_shorts.py -- --restore-surface
sh run_blender.sh fit_shorts.py
sh run_blender.sh finish_shorts.py
sh verify_shorts.sh
```

[Fit script](fit_shorts.py) · [Lining finish](finish_shorts.py) · [Checker adapter](check_shorts.py) · [Render script](render_shorts.py)

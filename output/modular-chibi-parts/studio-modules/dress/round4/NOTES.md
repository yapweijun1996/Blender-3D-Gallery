# Studio A-line dress · Round 4

**Motion gate failed.** The exported GLB was reimported and checked in Blender 5.1.2 at 1,260 poses. The seven legacy clips have zero inside vertices, zero triangle-overlap pairs, and at least 0.5 mm of clearance. Remaining gate failures occur in sit_down, sit_idle, stand_up, hold_item.

## Deliverables

- [Skinned dress GLB](dress_v4.glb) with 3,844 triangles and 2,500,412 bytes.
- [Editable Blender source](dress_v4.blend) with 6,523,230 bytes. The master body is present as a fitting reference.
- [Fitting and replay script](fit_dress_r4.py), [six-view rest sheet](six_view.png), [sit_idle](sit_idle.png), and [hold_item](hold_item.png).
- [GLB structural readback](export_check.json), [Khronos glTF Validator](gltf_validator.json), and [render manifest](renders.json).

The GLB has 1 garment mesh, 65 joints, 0 animation clips, and a maximum of 4 influences. Khronos glTF Validator 2.0.0-dev.3.10 reported 0 errors and 0 warnings. Tripo material JSON and packed PNG bytes match round 3. All embedded images are 1024 × 1024. The UV audit retained 2,752 of 2,752 unique source coordinates and added 0. The welded surface has 4 boundary loops and 0 non-manifold shared edges.

Rest clearance is 1.200–29.657 mm at exported vertices. 0 vertices exceed 30 mm. Triangle-centre and edge-midpoint probes span 1.108–29.939 mm, with 0 probes above 30 mm.

GLB SHA-256 `be07369f6f1bb4a52303305f4653f1a8f2f8d017fc274f7954c1070c6e3b5ef8`.

## Vertex checker

[Results](motion_check.txt) · [All poses](motion_check.json)

| Clip | Samples | Max inside vertices | Min signed (mm) | Min frame | Failing poses |
| --- | ---: | ---: | ---: | ---: | ---: |
| rest | 1 | 0 | 1.200 | 1 | 0 |
| walk | 113 | 0 | 0.510 | 22 | 0 |
| run | 61 | 0 | 0.599 | 9 | 0 |
| wave | 129 | 0 | 1.202 | 0 | 0 |
| jump | 101 | 0 | 0.669 | 9 | 0 |
| idle | 177 | 0 | 1.096 | 80 | 0 |
| nod | 113 | 0 | 1.202 | 0 | 0 |
| dance | 129 | 0 | 0.757 | 54.5 | 0 |
| sit_down | 73 | 63 | -7.290 | 6.5 | 73 |
| sit_idle | 181 | 53 | -2.682 | 18 | 181 |
| stand_up | 61 | 68 | -7.182 | 25 | 61 |
| hold_item | 121 | 32 | -2.330 | 14 | 121 |


## Triangle-overlap checker

[Results](motion_check_tri.txt) · [All poses](motion_check_tri.json)

| Clip | Samples | Max overlap pairs | Min signed (mm) | Min frame | Failing poses |
| --- | ---: | ---: | ---: | ---: | ---: |
| rest | 1 | 0 | 1.200 | 1 | 0 |
| walk | 113 | 0 | 0.510 | 22 | 0 |
| run | 61 | 0 | 0.599 | 9 | 0 |
| wave | 129 | 0 | 1.202 | 0 | 0 |
| jump | 101 | 0 | 0.669 | 9 | 0 |
| idle | 177 | 0 | 1.096 | 80 | 0 |
| nod | 113 | 0 | 1.202 | 0 | 0 |
| dance | 129 | 0 | 0.757 | 54.5 | 0 |
| sit_down | 73 | 371 | -7.290 | 6.5 | 73 |
| sit_idle | 181 | 285 | -2.682 | 18 | 181 |
| stand_up | 61 | 371 | -7.182 | 25 | 61 |
| hold_item | 121 | 241 | -2.330 | 14 | 121 |


Counts are the maximum per pose. The minimum signed distance is a garment-vertex to body-surface measurement in both checkers. The checker scripts used the specified master, corrected legacy bank and added action bank. Frame loops were extended to include each half frame and both endpoints. Preview calls were omitted from the checkers, and Cycles CPU rendered the plates. The new bank used 30 fps and Blender 5 action slots. Pose-bone rotation modes were preserved.

## Remaining contacts

[Per-clip and per-zone diagnosis](failure_zones.json)

| Clip | Deepest vertex zone / body region | Signed distance / frame | Deepest intersecting face zone / body region | Probe distance / frame |
| --- | --- | --- | --- | --- |
| sit_down | bodice / RightForeArm | -7.290 mm at 6.5 | bodice / RightForeArm | -10.129 mm at 3.5 |
| sit_idle | shoulder and armpit / LeftArm | -2.682 mm at 18 | shoulder and armpit / Spine1 | -8.391 mm at 14.5 |
| stand_up | bodice / RightForeArm | -7.182 mm at 25 | bodice / RightForeArm | -10.645 mm at 27.5 |
| hold_item | shoulder and armpit / LeftArm | -2.330 mm at 14 | bodice / LeftForeArm | -8.339 mm at 9.5 |

Negative values are penetration depths. Positive values under 0.5 mm are clearance shortfalls. Face probes sample intersection segments and the interiors of contacting triangles. Their values are separate from the gate's vertex minimum.

## Fitting

The fit starts from the shipped [Round 3 GLB](../round3/dress_v3.glb) and reuses the authored material from its Blender source. The fitter welds position duplicates for editing and retains per-loop UVs. It samples every integer and half frame and transports each vertex's worst contact direction through its skin transform. The starting displacement is the required clearance plus a 2 mm margin, bounded to 30 mm. A neighborhood Laplacian spreads the displacement and restores the required component after each pass.

The fitter evaluates local offsets and normalized joint blends against the swept poses. It uses the nearest body skin field and neighboring garment weights as candidate supports around the cuffs, armpits, hips and skirt. Accepted patches preserve the legacy clearance where the source already passes. A tighter left-armhole patch addresses the 0.132 mm walk minimum in round 3. A rest-only pass checks the 30 mm hem limit and adjusts excessive witnesses when present. Trial subdivision around crossing triangles increased legacy overlap counts. The delivered fit retains the round-3 face layout.

Run with the guarded Blender 5.1.2 executable and `DYLD_INSERT_LIBRARIES` specified in the task. Use a temporary directory under round4 for Blender's working files. The local `build` stage starts from the shipped seed. To rerun the checks and plates on the delivered export, use the following command from round4.

```sh
mkdir -p .work
TMPDIR="$PWD/.work" PYTHONDONTWRITEBYTECODE=1 VECLIB_MAXIMUM_THREADS=1 \
  "$BLENDER" -b -noaudio -t 6 --factory-startup --disable-autoexec \
  --python-exit-code 1 --python fit_dress_r4.py -- check verify replay render zones
```

The delivered Blender source re-exports to the identical GLB bytes in the [replay audit](blend_replay.json). The complete fit was run in stages from round 3.

## Renders

The rest-sheet order is front, back, left, right, three-quarter and dress only. The action plates use each clip's minimum signed-distance frame on the delivered GLB. Those frames are 18 for sit_idle and 14 for hold_item.

The independent visual review matched the GLB and all three PNG hashes. The pastel Tripo finish, round neck, cap sleeves and loose A-line shape remain recognizable at rest. A small cuff flare, side-waist crease and front hem point are more pronounced than in Round 3. The sit_idle plate shows a dark underarm crease and bunching along the near hip and upper thigh, with a curled section of hem. The hold_item plate shows a continuous bodice and skirt, with a pinched underarm and upturned tip at the lowered-arm sleeve.

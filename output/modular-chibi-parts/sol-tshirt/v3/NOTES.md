# Short-sleeve T-shirt v3

**Acceptance status** — The rest pose passes both collision checks. All seven clips still have garment/body intersections. The run capture also has visible cloth creases.

## Build and module

Run the builder with the supplied guarded Blender 5.1.2 binary and the repository master and motion files in their original locations.

```sh
"$BLENDER" -b -noaudio --python make_tshirt_v3.py -- --check --cpu-render
```

The builder extracts a quad-dominant shell from a regular 9 mm signed-distance grid, adapts it to the body surface and cuts four openings. It fairs the crew rim in height and transfers barycentric body weights with two diffusion passes. The hem follows the shorts waist line because the waistband is baked into the master body. Its height is 0.417 m and the Hips joint is at 0.373 m. Both cuff planes intersect their shoulder-to-elbow axes at 40.00%.

The GLB has **3,746 triangles and 132,516 bytes**. The editable Blend is 1,089,260 bytes and has 1,824 quad faces. Median and 95th-percentile torso grid edges are 7.32 mm and 9.34 mm. The measured bind torso clearance is 3.089–5.157 mm. The reimported module has 0 nonadjacent rest self-intersection pairs.

The GLB contains one flat sea-green material, one skinned shirt mesh, 65 matching Mixamo joint names and at most four normalized influences. The export excludes the body and animation. The Blend includes Base_Body as fit context.

Khronos glTF Validator 2.0.0-dev.3.10 returned **0 errors and 0 warnings**. A second build in a separate local output folder produced a byte-identical GLB. [Validator report](gltf_validation.json) · [Geometry audit](geometry_check.json)

GLB SHA-256 `803060a461f42c27c1255ed9deeb828d3a1d4e62ef72817dddbdbb37dd744ba3`

## Fitting result

The builder evaluated signed distances and triangle overlaps over the rest pose and all 415 integer clip frames per evaluation. It tried eight fit updates using the worst needed clearance plus a 0.8 mm margin in motion, a 20 mm offset cap and constrained Laplacian passes. The subdivided trial split 48 long contact edges. The minimum combined count of vertex and triangle failures occurred on the initial shell. Intermediate variants reduced some local deficits and introduced other contacts. The exported shell therefore retains the original offset and grid. The supplied checkers ran on the final GLB with their original measurement code. Their identical render poses were captured once using CPU Cycles.

Separate inspection of the master found arm-to-torso self-intersection during representative walk and run frames. Enlarging the shell along the supporting torso normal can push it farther into the opposing arm. The remaining contacts are recorded below. [Dense build measurements](dense_motion.json)

## Vertex checker RESULT

| Pose | Max vertices inside | Min signed distance (m) |
| --- | ---: | ---: |
| rest | 0 | 0.003600 |
| walk | 91 | -0.009500 |
| run | 63 | -0.007800 |
| wave | 62 | -0.006600 |
| jump | 63 | -0.006000 |
| idle | 72 | -0.005600 |
| nod | 64 | -0.005800 |
| dance | 32 | -0.002600 |

[Vertex JSON](motion_check.json) · [Vertex RESULT log](motion_check.log)

## Triangle checker RESULT

| Pose | Max overlapping triangle pairs | Min signed vertex distance (m) |
| --- | ---: | ---: |
| rest | 0 | 0.003600 |
| walk | 339 | -0.008800 |
| run | 325 | -0.008200 |
| wave | 270 | -0.006500 |
| jump | 284 | -0.006400 |
| idle | 296 | -0.005600 |
| nod | 274 | -0.005800 |
| dance | 112 | -0.002600 |

[Triangle JSON](motion_check_tri.json) · [Triangle RESULT log](motion_check_tri.log)

## Dense reimport of the final GLB

The independent BVH evaluation used all 416 rest and integer-frame states. The triangle count column counts exact BVH overlap pairs at the peak frame. The depth column measures the deepest sampled point on overlapping triangles on a six-step barycentric grid. Signed depth uses the nearest body triangle normal. Subframes were outside this measurement.

| Clip | Peak pairs and frame | Deepest vertex and frame | Deepest triangle sample and frame |
| --- | --- | --- | --- |
| walk | 341 at 41 | 9.475 mm at 33, right front torso against right upper arm | 9.475 mm at 33, right front torso against right upper arm |
| run | 325 at 9 | 8.278 mm at 28, left front torso against left upper arm | 8.189 mm at 9, left front torso against left upper arm |
| wave | 270 at 0 | 6.562 mm at 16, left back torso against left forearm | 6.562 mm at 16, left back torso against left forearm |
| jump | 284 at 3 | 7.253 mm at 40, left front torso against left forearm | 8.755 mm at 8, left front torso against left forearm |
| idle | 297 at 55 | 5.636 mm at 54, left back torso against left forearm | 5.636 mm at 54, left back torso against left forearm |
| nod | 274 at 15 | 5.766 mm at 17, left back torso against left forearm | 5.925 mm at 19, left hem against left forearm |
| dance | 116 at 40 | 2.624 mm at 40, left sleeve against left armhole | 2.663 mm at 44, left armhole against left upper arm |

[Full reimport results and peak zones](dense_export_check.json)

## Visual review

An independent reviewer inspected the six final captures. The crew neckline is rounded, the hem is level in bind pose and sits just above the waistband, and the short cuff lengths look even. The rest close-ups show small flared hem corners and shallow creases at the cuff-to-underarm junctions. The run capture retains creases below the sleeve on screen left and across the mid-to-lower torso. Tidy cloth in run remains open.

[Rest front](rest_front.png) · [Rest three-quarter](rest_three_quarter.png) · [Walk frame 23](walk.png) · [Run frame 12](run.png) · [Wave frame 25](wave.png) · [Jump frame 20](jump.png)

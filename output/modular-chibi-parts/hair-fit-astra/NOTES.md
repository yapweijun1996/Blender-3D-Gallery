# Chibi chestnut bob

The GLB contains one textured mesh and one skin with 2,889 triangles. The editable Blender file includes the master body as a fitting reference. The root-level GLB mesh uses the master origin, glTF +Y up and +Z front. All 65 joint names match the base in order and have identical child-bone hierarchies. Inverse bind matrices match to 0.000001 absolute tolerance. The mesh uses at most 2 normalized influences. Head carries the bob, with up to 10.50% Neck weight at the lower rear. The GLB has no clips or body geometry.

## Extraction and fit

The original Tripo mesh faces Blender +X. Its front-facing skin shell contains 1,299 of the 5,253 triangles. UV-seam welding separates that shell, the 3,860-triangle main hair mass, a 92-triangle temple lock and a two-triangle internal sliver. The build removes the face and sliver, cuts the deep lining out of the original strands and opens the lower curtains around the master ears. A mirrored copy of the intact Tripo temple lock replaces the fused opposite lock. The imported UVs and base-color image supply the strand detail. The embedded 2,048-pixel atlas is reduced to 1,024 × 1,024 and tinted chestnut in the material.

The vertical gap above the scalp at Blender (x=0.001, y=0) in the rest pose measures 0.007329 m. Across 5,941 radial samples of the continuous upper cap, first-layer clearance was 0.004651 to 0.010675 m. The audit covers every two degrees of azimuth and elevation from 25° above horizontal through the pole, and all rays hit hair. Sculpted outer locks and free ends have greater standoff. The lower and face openings let the module fit over the head. The reference is a single front image with a blank face. Eye clearance is judged on the actual master, and the rear shape follows the supplied 3D source.

The rebuilt side locks frame the outer eye corners. Both iris centers and both ears are visible from the front. The original rear cap is smoother than the separated front locks. Small highlight and shading variations remain near the temples. One pinpoint on the upper left profile falls inside a continuous hair triangle and corresponds to a darker region of the base-color atlas. The lower rim is intentionally open, with narrow gaps between separate locks.

## Export checks

Khronos glTF Validator 2.0.0-dev.3.10 reported 0 errors and 0 warnings. Blender 5.1.2 reimported the saved GLB. The supplied checker ran on the original master and motion GLB. Native Workbench aborted headlessly on macOS. The unchanged checker completed using a frame handler that switches only rendering to Cycles CPU. Each standard clip RESULT uses its 12 requested sample frames. The supplemental pass checks every integer frame, including both endpoints, for signed vertex clearance and triangle-to-triangle intersections against the evaluated body. All distances are in metres. Fractional times between integer frames are outside this audit.

| Clip | RESULT max inside | RESULT min distance | Full frames | Full max inside | Full min distance | Full max intersecting triangle pairs |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| rest | 0 | 0.005972 | 1 | 0 | 0.005972 | 0 |
| walk | 0 | 0.005900 | 57 | 0 | 0.005899 | 0 |
| run | 0 | 0.005700 | 31 | 0 | 0.005717 | 0 |
| wave | 0 | 0.005900 | 65 | 0 | 0.005913 | 0 |
| jump | 0 | 0.006000 | 51 | 0 | 0.005956 | 0 |
| idle | 0 | 0.006000 | 89 | 0 | 0.005962 | 0 |
| nod | 0 | 0.006000 | 57 | 0 | 0.005951 | 0 |
| dance | 0 | 0.006000 | 65 | 0 | 0.005969 | 0 |

## Files and reproduction

Run the supplied guarded Blender executable in background mode with `--python fit_hair.py`. Keep the repository input layout, the supplied `motion_check.py` beside the build script and the installed validator available. The script builds the blend and GLB, checks the exported file, renders all five PNGs and writes this report. `motion_check.json` is the unmodified checker's output. The 3×2 fit sheet shows the reimported GLB on the master. Top row is front, left and right three-quarter. Bottom row is left profile, rear and right profile. The orthographic camera is fixed (0.55 m, 520 pixels per view, Cycles CPU).

| Artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| hair_bob_v1.blend | 1,308,179 | `77ba009b2a0f0180a0790daa5bd0d0ff64a6bdc042db4659e449b7f654c9e9fb` |
| hair_bob_v1.glb | 415,916 | `3c8c3349e7f06924641f5ca20d5bdc7c92efe5d7454d6302646b14e957ffb42e` |
| fit_views.png | 1,953,448 | `b9d9e39052754153775ef0a31daf6ecb51f98581d3bb5342ae45af5103cde20f` |
| walk.png | 281,914 | `c7857ae6c334e09a810355d6afb2239829a2fafcc9dd5e14134276a81b740519` |
| run.png | 280,293 | `2c1cd8c71bc5d2a0e1912e6a785a577906737448e3dd8a90c9c29d01001c1684` |
| wave.png | 280,061 | `e9e3f6c3d9b4423756e12402274a1c51df44e8bdf9f80d127308d5da58afee20` |
| jump.png | 280,621 | `30647c369ebdc3e0458e19dcb9983ccd08ec6c4bc2386eb3d0752b0a1210c7b0` |

Source GLB `a557931e35a2b1e66899483d8a3c0cc79e222cffc61683c8cf90651cea6e9569`  
Master blend `0339318b375836ab8891e49bda178da7e6f115e012e83385d9f8850949a7bd6f`  
Motion GLB `ffccda1ba2a50eb10948853e03d17f0d095cd9b953d644c03c4fb9cb95529410`  
Reference PNG `b46ed818f83ebebc61ad95ad8bf784f65ee5246cebc1f87434d9bf5e35537939`

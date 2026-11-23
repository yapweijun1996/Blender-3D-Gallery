# Chibi hand gesture library

The editable body opens in its bind pose. Choose a hand action at frame 1 in the Action Editor or apply its pose asset. The static GLB and the separate animation GLB share the same rest hierarchy. Each clip keys 20 digit bones on its named side. All 18 wrists remain at bind, including thumbs-up. Each native pose asset includes a 256 × 224 preview.

## Files

| File | Contents |
| --- | --- |
| [hands_gestures.blend](hands_gestures.blend) | Skinned body, 65-bone rig and 18 one-frame pose assets |
| [base_body.glb](base_body.glb) | Rest body, skin and skeleton |
| [hand_gestures.glb](hand_gestures.glb) | Standalone skeleton and 18 rotation clips |
| [hand_gestures.json](hand_gestures.json) | Authoritative local XYZ rotation deltas in degrees, keyed by clip and bone |
| [renders/](renders/) · [contact_sheet.png](contact_sheet.png) | 54 Cycles CPU orthographic renders and a labelled index with projected 40 mm gauges on the two grip side views |
| [hand_check.json](hand_check.json) · [hand_check.log](hand_check.log) | All measurements, clip names, file hashes and printed validation |

## Rig and surface

Finger names and parent links come from the repaired master. Rest rolls now follow a common local convention. Finger pivots track the modestly narrowed hand. The original UV seams are retained. Local edge subdivision and quad recovery support the dorsal MCP and interphalangeal knuckles, tapered shafts, palmar pad and thumb mound. The palm heel slopes into the dorsal knuckle line. Vertices on the free digit shafts use only their respective four-bone chains. The central palmar patch is rigid on Hand. The thenar pad blends between Hand and the thumb.

Local +Y runs from head to tail. Positive rotation about X moves the +Y shaft toward local +Z. The four long fingers have +Z aimed toward the palmar side in bind space. On the thumb +Z aims obliquely across the hand, with a palmar component, so +X gives opposition. The local Z rotation controls the independent spread or abduction motion. Local Y supplies twist when needed. The signs below apply to segments 1–4. Segment 4 remains neutral in the supplied poses.

| Digit | Left flexion | Right flexion | Left spread / abduction | Right spread / abduction |
| --- | --- | --- | --- | --- |
| Index | +X | +X | +Z toward thumb / −Y | −Z toward thumb / −Y |
| Middle | +X | +X | +Z for radial fan | −Z for radial fan |
| Ring | +X | +X | −Z for ulnar fan / +Y | +Z for ulnar fan / +Y |
| Pinky | +X | +X | −Z for ulnar fan / +Y | +Z for ulnar fan / +Y |
| Thumb | +X across palm | +X across palm | +Z palmar abduction / −Z dorsal lift | −Z palmar abduction / +Z dorsal lift |

The L/R signs refer to the character. The world is Blender Z-up, with the character looking along −Y. Reversing the stated signs reverses the movement. Per-segment rest X/Y/Z unit vectors are recorded under `rest.*.local_axes_world` in hand_check.json.

## Counts and rest measurements

| Measure | Result |
| --- | --- |
| Whole mesh | 6,010 Blender vertices · 9,512 triangles |
| Armature | 65 bones · 65 vertex groups · 0 changed parents |
| Outside the hands | 2,790 original vertices at |X| ≤ 0.271 m · maximum rest displacement 0.000000000 m · 0 modified weight maps |
| Maximum non-finger bind matrix component difference | 0 |
| Skin influences | 4 maximum · 0 above four · 0 unweighted · maximum sum error 1.00582838e-07 |
| Finger bleed | 0 vertices above 0.2 from two finger chains · 0 mixing chains at any positive weight |
| Static glTF | 1 mesh · 1 skin · 65 joints · 0 animations · 9,512 triangles |
| Animation glTF | 0 meshes · 66 nodes · 18 named clips · one quaternion sample at 0 s per channel |
| Export differences | weights 1.1920929e-07 · inverse bind identity 3.57627869e-07 · rest node transforms 0 · local quaternion components 1.49011612e-07 |
| Reimport into Blender | 18 Actions · rest maximum 0.000276 mm · posed maximum 0.000522 mm across every vertex and gesture |

| Rest measure | Left | Right |
| --- | --- | --- |
| Triangles in hand | 2628 | 2626 |
| Quad faces in hand | 972 | 975 |
| Nonmanifold edges after matching seam positions | 0 | 0 |
| Palmar centre, world metres | [0.2987, -0.01149, 0.54319] | [-0.29846, -0.01027, 0.54331] |
| Volume centre, world metres | [0.2987, -0.01149, 0.55828] | [-0.29846, -0.01027, 0.55845] |
| Palmar surface normal | [0.20484, 0.05774, -0.97709] | [-0.19493, 0.07294, -0.9781] |
| Angle from world down, degrees | 12.288 | 12.013 |
| Thumb direction from root to skin tip | [0.62462, -0.77224, -0.11621] | [-0.63097, -0.75873, -0.16188] |
| Free shaft vertices checked | 850 | 840 |
| Shaft vertices with foreign influences | 0 | 0 |
| Central palmar vertices checked | 19 | 17 |
| Minimum central Hand weight | 1.0 | 1.0 |
| Thenar vertices checked | 31 | 30 |
| Thenar Hand weight range | [0.424959, 0.840007] | [0.460594, 0.840027] |
| Thenar thumb weight range | [0.159993, 0.575041] | [0.159973, 0.539406] |

A hand triangle has all three original-space vertices beyond the 0.270 m wrist cut on that side. Body comparisons use original vertex indices. Render normals on the unedited body are restored from the master. Seam-aware edge counts use coincident rest positions.

## Pose measurements

All distances below are millimetres. The centre is fixed halfway in plan view between the wrist and the mean of the four long-finger MCPs. The palmar landmark is the lower surface ray hit. The volume landmark is halfway between the palmar and dorsal ray hits. Both landmarks follow the wrist. The tip is the centroid of distinct skinned surface vertices within 1.8 mm of the distal extremum along each rest digit. Overshooting terminal bone tails do not enter the measurement.

XYZ uses Blender world axes relative to the stated centre. Skin gap is the shortest distance from the tip landmark to the posed palmar surface patch. The thumb/index pad gap uses bidirectional distal surface sampling. Intersection tolerance is zero intersecting, nonadjacent triangle pairs in the tested hand and wrist surface. Triangles sharing a rest-space vertex, including a UV-seam duplicate, are excluded. This tests the sampled still poses. Interpolation between them depends on the animation system.

| Actual glTF clip | Rotation channels | Thumb/index tip | Distal pad gap | Thumb above other four¹ | Triangle intersections | Max reimport error |
| --- | --- | --- | --- | --- | --- | --- |
| hand_fist_L | 20 | 24.194 | 11.2488 | -4.634 | 0 | 0.000342 |
| hand_open_relaxed_L | 20 | 57.013 | 36.918 | -10.213 | 0 | 0.000323 |
| hand_point_L | 20 | 93.081 | 71.0201 | -35.659 | 0 | 0.000342 |
| hand_thumbs_up_L | 20 | 61.059 | 42.5296 | 50.721 | 0 | 0.000342 |
| hand_peace_L | 20 | 83.011 | 60.612 | -35.656 | 0 | 0.000342 |
| hand_ok_L | 20 | 3.854 | 0.0051 | -17.152 | 0 | 0.000323 |
| hand_grip_small_L | 20 | 44.955 | 39.8889 | -11.642 | 0 | 0.000365 |
| hand_pinch_L | 20 | 4.187 | 0.0911 | -6.296 | 0 | 0.000323 |
| hand_open_wide_L | 20 | 68.062 | 47.7076 | -10.947 | 0 | 0.000323 |
| hand_fist_R | 20 | 16.815 | 3.1483 | -6.554 | 0 | 0.000465 |
| hand_open_relaxed_R | 20 | 64.976 | 43.7243 | -17.411 | 0 | 0.000334 |
| hand_point_R | 20 | 84.02 | 61.0629 | -31.103 | 0 | 0.000455 |
| hand_thumbs_up_R | 20 | 60.234 | 41.3046 | 44.824 | 0 | 0.000465 |
| hand_peace_R | 20 | 89.922 | 66.8121 | -36.009 | 0 | 0.000455 |
| hand_ok_R | 20 | 3.014 | 0.0011 | -19.363 | 0 | 0.000471 |
| hand_grip_small_R | 20 | 45.008 | 40.4939 | -11.551 | 0 | 0.000522 |
| hand_pinch_R | 20 | 3.354 | 0.0697 | -13.225 | 0 | 0.00052 |
| hand_open_wide_R | 20 | 74.684 | 52.3896 | -18.756 | 0 | 0.00043 |

¹ Signed world-Z difference. The thumbs-up poses require a positive value.

### Grip cylinder

The same infinite cylinder was tested against every posed hand and wrist triangle. Its axis runs diagonally across the palm. The clearance calculation projects each filled triangle to the plane perpendicular to the cylinder and measures the exact minimum distance from the axis. The contact sheet overlays the measured gauge on the two axial thumb-side thumbnails. The full-size PNGs show the hand alone.

| Side | Gauge diameter | Axis point (world mm) | Unit direction | Palm / Index / Middle / Ring / Pinky / Thumb distance to axis | Penetrating triangles |
| --- | --- | --- | --- | --- | --- |
| L | 40 | 303.699, -11.487, 520.190 | -0.410, 0.912, 0.000 | 21.9534, 20.1706, 20.1792, 20.1887, 20.1935, 20.1794 | 0 |
| R | 40 | -303.460, -10.269, 520.307 | 0.410, 0.912, 0.000 | 20.9786, 20.1696, 20.1814, 20.1897, 20.1968, 20.1789 | 0 |

### All five fingertips in all 18 actions

| Clip | Digit | XYZ from palmar centre | Distance to palmar centre | XYZ from volume centre | Distance to volume centre | Gap to palmar skin |
| --- | --- | --- | --- | --- | --- | --- |
| hand_fist_L | Index | 1.140, -16.299, -1.900 | 16.449 | 1.140, -16.299, -16.990 | 23.572 | 1.902 |
| hand_fist_L | Middle | 5.891, -5.102, -0.844 | 7.839 | 5.891, -5.102, -15.935 | 17.738 | 1.582 |
| hand_fist_L | Ring | 8.508, 6.785, -0.336 | 10.888 | 8.508, 6.785, -15.426 | 18.878 | 1.648 |
| hand_fist_L | Pinky | 2.768, 16.986, -0.467 | 17.216 | 2.768, 16.986, -15.557 | 23.199 | 2.551 |
| hand_fist_L | Thumb | 2.291, 7.672, -4.970 | 9.424 | 2.291, 7.672, -20.060 | 21.599 | 5.681 |
| hand_open_relaxed_L | Index | 83.117, -30.684, 3.229 | 88.659 | 83.117, -30.684, -11.861 | 89.39 | 58.375 |
| hand_open_relaxed_L | Middle | 101.657, -12.623, -8.419 | 102.783 | 101.657, -12.623, -23.510 | 105.1 | 74.133 |
| hand_open_relaxed_L | Ring | 102.188, 10.475, -16.019 | 103.965 | 102.188, 10.475, -31.109 | 107.331 | 72.107 |
| hand_open_relaxed_L | Pinky | 88.518, 30.570, -20.599 | 95.887 | 88.518, 30.570, -35.690 | 100.218 | 63.834 |
| hand_open_relaxed_L | Thumb | 29.486, -47.111, -6.984 | 56.014 | 29.486, -47.111, -22.074 | 59.8 | 23.249 |
| hand_point_L | Index | 83.543, -35.212, 21.079 | 93.079 | 83.543, -35.212, 5.989 | 90.859 | 58.425 |
| hand_point_L | Middle | 5.891, -5.102, -0.844 | 7.839 | 5.891, -5.102, -15.935 | 17.738 | 1.508 |
| hand_point_L | Ring | 8.508, 6.785, -0.336 | 10.888 | 8.508, 6.785, -15.426 | 18.878 | 1.648 |
| hand_point_L | Pinky | 2.768, 16.986, -0.467 | 17.216 | 2.768, 16.986, -15.557 | 23.199 | 2.551 |
| hand_point_L | Thumb | 3.671, -3.384, -14.579 | 15.411 | 3.671, -3.384, -29.669 | 30.087 | 14.887 |
| hand_thumbs_up_L | Index | 1.140, -16.299, -1.900 | 16.449 | 1.140, -16.299, -16.990 | 23.572 | 1.719 |
| hand_thumbs_up_L | Middle | 5.891, -5.102, -0.844 | 7.839 | 5.891, -5.102, -15.935 | 17.738 | 1.497 |
| hand_thumbs_up_L | Ring | 8.508, 6.785, -0.336 | 10.888 | 8.508, 6.785, -15.426 | 18.878 | 1.648 |
| hand_thumbs_up_L | Pinky | 2.768, 16.986, -0.467 | 17.216 | 2.768, 16.986, -15.557 | 23.199 | 2.55 |
| hand_thumbs_up_L | Thumb | 11.678, -46.020, 50.386 | 69.231 | 11.678, -46.020, 35.295 | 59.161 | 31.089 |
| hand_peace_L | Index | 81.916, -43.308, 21.023 | 95.014 | 81.916, -43.308, 5.932 | 92.849 | 59.976 |
| hand_peace_L | Middle | 106.344, -8.080, 9.964 | 107.115 | 106.344, -8.080, -5.127 | 106.773 | 74.666 |
| hand_peace_L | Ring | 11.139, 2.605, -11.822 | 16.451 | 11.139, 2.605, -26.913 | 29.243 | 13.344 |
| hand_peace_L | Pinky | 2.768, 16.986, -0.467 | 17.216 | 2.768, 16.986, -15.557 | 23.199 | 2.551 |
| hand_peace_L | Thumb | 17.495, -4.976, -14.634 | 23.345 | 17.495, -4.976, -29.724 | 34.847 | 17.206 |
| hand_ok_L | Index | 21.286, -53.908, -14.123 | 59.654 | 21.286, -53.908, -29.213 | 64.904 | 29.113 |
| hand_ok_L | Middle | 104.222, -12.013, -0.600 | 104.914 | 104.222, -12.013, -15.690 | 106.079 | 73.666 |
| hand_ok_L | Ring | 107.479, 20.633, 0.766 | 109.444 | 107.479, 20.633, -14.324 | 110.375 | 72.775 |
| hand_ok_L | Pinky | 94.250, 48.469, 2.300 | 106.007 | 94.250, 48.469, -12.791 | 106.751 | 67.391 |
| hand_ok_L | Thumb | 19.278, -50.701, -14.852 | 56.239 | 19.278, -50.701, -29.942 | 61.958 | 27.019 |
| hand_grip_small_L | Index | 34.742, -16.207, -17.113 | 41.982 | 34.742, -16.207, -32.203 | 50.067 | 27.334 |
| hand_grip_small_L | Middle | 29.424, -3.780, -20.215 | 35.899 | 29.424, -3.780, -35.306 | 46.115 | 27.285 |
| hand_grip_small_L | Ring | 22.544, 12.495, -22.392 | 34.144 | 22.544, 12.495, -37.483 | 45.49 | 26.714 |
| hand_grip_small_L | Pinky | 16.618, 25.280, -22.360 | 37.619 | 16.618, 25.280, -37.450 | 48.143 | 27.688 |
| hand_grip_small_L | Thumb | -4.466, -34.864, -28.754 | 45.412 | -4.466, -34.864, -43.845 | 56.194 | 26.77 |
| hand_pinch_L | Index | 29.657, -43.666, -13.333 | 54.443 | 29.657, -43.666, -28.423 | 59.951 | 27.016 |
| hand_pinch_L | Middle | 5.524, -5.424, -11.251 | 13.657 | 5.524, -5.424, -26.341 | 27.456 | 11.746 |
| hand_pinch_L | Ring | 7.329, 6.788, -8.991 | 13.44 | 7.329, 6.788, -24.082 | 26.071 | 10.142 |
| hand_pinch_L | Pinky | 2.107, 18.695, -7.510 | 20.257 | 2.107, 18.695, -22.601 | 29.406 | 9.642 |
| hand_pinch_L | Thumb | 26.763, -46.655, -13.806 | 55.53 | 26.763, -46.655, -28.897 | 61.057 | 27.784 |
| hand_open_wide_L | Index | 81.419, -44.264, 22.500 | 95.366 | 81.419, -44.264, 7.410 | 92.969 | 60.605 |
| hand_open_wide_L | Middle | 106.027, -18.724, 21.454 | 109.784 | 106.027, -18.724, 6.364 | 107.856 | 75.224 |
| hand_open_wide_L | Ring | 110.290, 16.890, 19.639 | 113.29 | 110.290, 16.890, 4.548 | 111.668 | 73.904 |
| hand_open_wide_L | Pinky | 96.340, 47.923, 15.817 | 108.757 | 96.340, 47.923, 0.727 | 107.603 | 67.3 |
| hand_open_wide_L | Thumb | 17.136, -63.763, 11.553 | 67.028 | 17.136, -63.763, -3.537 | 66.12 | 26.472 |
| hand_fist_R | Index | -1.654, -15.523, -2.805 | 15.861 | -1.654, -15.523, -17.949 | 23.788 | 2.325 |
| hand_fist_R | Middle | -6.377, -6.215, -0.780 | 8.939 | -6.377, -6.215, -15.924 | 18.244 | 1.311 |
| hand_fist_R | Ring | -3.041, 6.453, -1.069 | 7.213 | -3.041, 6.453, -16.213 | 17.713 | 1.775 |
| hand_fist_R | Pinky | -0.427, 18.148, -0.084 | 18.153 | -0.427, 18.148, -15.228 | 23.694 | 2.14 |
| hand_fist_R | Thumb | -1.087, 0.839, -6.637 | 6.778 | -1.087, 0.839, -21.781 | 21.825 | 6.734 |
| hand_open_relaxed_R | Index | -83.316, -28.033, 5.023 | 88.049 | -83.316, -28.033, -10.121 | 88.486 | 57.929 |
| hand_open_relaxed_R | Middle | -102.142, -11.237, -4.528 | 102.858 | -102.142, -11.237, -19.671 | 104.624 | 74.079 |
| hand_open_relaxed_R | Ring | -101.829, 10.671, -14.460 | 103.402 | -101.829, 10.671, -29.604 | 106.58 | 77.074 |
| hand_open_relaxed_R | Pinky | -88.087, 31.321, -17.156 | 95.05 | -88.087, 31.321, -32.300 | 98.912 | 67.116 |
| hand_open_relaxed_R | Thumb | -24.019, -48.097, -12.388 | 55.17 | -24.019, -48.097, -27.532 | 60.401 | 26.4 |
| hand_point_R | Index | -82.846, -32.409, 22.772 | 91.828 | -82.846, -32.409, 7.628 | 89.286 | 56.929 |
| hand_point_R | Middle | -6.377, -6.215, -0.780 | 8.939 | -6.377, -6.215, -15.924 | 18.244 | 1.267 |
| hand_point_R | Ring | -3.041, 6.453, -1.069 | 7.213 | -3.041, 6.453, -16.213 | 17.713 | 1.775 |
| hand_point_R | Pinky | -0.427, 18.148, -0.084 | 18.153 | -0.427, 18.148, -15.228 | 23.694 | 2.14 |
| hand_point_R | Thumb | -8.036, -10.150, -8.331 | 15.395 | -8.036, -10.150, -23.475 | 26.808 | 8.406 |
| hand_thumbs_up_R | Index | -1.654, -15.523, -2.805 | 15.861 | -1.654, -15.523, -17.949 | 23.788 | 2.191 |
| hand_thumbs_up_R | Middle | -6.377, -6.215, -0.780 | 8.939 | -6.377, -6.215, -15.924 | 18.244 | 1.267 |
| hand_thumbs_up_R | Ring | -3.041, 6.453, -1.069 | 7.213 | -3.041, 6.453, -16.213 | 17.713 | 1.775 |
| hand_thumbs_up_R | Pinky | -0.427, 18.148, -0.084 | 18.153 | -0.427, 18.148, -15.228 | 23.694 | 2.14 |
| hand_thumbs_up_R | Thumb | -8.202, -51.920, 44.740 | 69.026 | -8.202, -51.920, 29.596 | 60.323 | 29.436 |
| hand_peace_R | Index | -81.253, -40.436, 22.695 | 93.553 | -81.253, -40.436, 7.551 | 91.073 | 58.535 |
| hand_peace_R | Middle | -105.380, -2.583, 21.130 | 107.509 | -105.380, -2.583, 5.986 | 105.582 | 73.691 |
| hand_peace_R | Ring | -3.041, 6.453, -1.069 | 7.213 | -3.041, 6.453, -16.213 | 17.713 | 1.775 |
| hand_peace_R | Pinky | -0.427, 18.148, -0.084 | 18.153 | -0.427, 18.148, -15.228 | 23.694 | 2.14 |
| hand_peace_R | Thumb | -8.721, -1.342, -13.314 | 15.973 | -8.721, -1.342, -28.458 | 29.795 | 14.25 |
| hand_ok_R | Index | -17.025, -52.603, -13.177 | 56.838 | -17.025, -52.603, -28.321 | 62.121 | 26.285 |
| hand_ok_R | Middle | -104.268, -10.617, 3.314 | 104.86 | -104.268, -10.617, -11.830 | 105.473 | 74.364 |
| hand_ok_R | Ring | -106.701, 20.646, 2.158 | 108.702 | -106.701, 20.646, -12.986 | 109.453 | 77.022 |
| hand_ok_R | Pinky | -92.931, 48.622, 5.354 | 105.018 | -92.931, 48.622, -9.790 | 105.338 | 69.467 |
| hand_ok_R | Thumb | -14.453, -53.937, -14.009 | 57.57 | -14.453, -53.937, -29.153 | 62.992 | 26.017 |
| hand_grip_small_R | Index | -37.215, -22.101, -16.836 | 46.442 | -37.215, -22.101, -31.980 | 53.816 | 27.683 |
| hand_grip_small_R | Middle | -29.298, -3.415, -20.365 | 35.843 | -29.298, -3.415, -35.509 | 46.162 | 27.015 |
| hand_grip_small_R | Ring | -22.434, 12.451, -22.356 | 34.03 | -22.434, 12.451, -37.500 | 45.437 | 26.665 |
| hand_grip_small_R | Pinky | -16.213, 26.255, -22.191 | 38.008 | -16.213, 26.255, -37.335 | 48.436 | 27.52 |
| hand_grip_small_R | Thumb | 4.765, -33.500, -28.386 | 44.167 | 4.765, -33.500, -43.530 | 55.135 | 24.525 |
| hand_pinch_R | Index | -25.671, -39.929, -21.279 | 52.02 | -25.671, -39.929, -36.423 | 59.833 | 30.089 |
| hand_pinch_R | Middle | -6.160, -5.994, -11.033 | 13.986 | -6.160, -5.994, -26.177 | 27.552 | 11.456 |
| hand_pinch_R | Ring | -3.248, 6.290, -10.027 | 12.275 | -3.248, 6.290, -25.171 | 26.148 | 10.685 |
| hand_pinch_R | Pinky | -1.192, 18.288, -7.022 | 19.626 | -1.192, 18.288, -22.166 | 28.761 | 8.968 |
| hand_pinch_R | Thumb | -22.870, -38.400, -20.247 | 49.067 | -22.870, -38.400, -35.391 | 57.01 | 27.535 |
| hand_open_wide_R | Index | -80.695, -41.374, 24.140 | 93.841 | -80.695, -41.374, 8.996 | 91.128 | 59.161 |
| hand_open_wide_R | Middle | -104.908, -17.193, 25.170 | 109.246 | -104.908, -17.193, 10.026 | 106.779 | 75.053 |
| hand_open_wide_R | Ring | -109.035, 16.941, 20.762 | 112.279 | -109.035, 16.941, 5.618 | 110.486 | 77.74 |
| hand_open_wide_R | Pinky | -94.533, 48.035, 18.557 | 107.649 | -94.533, 48.035, 3.413 | 106.092 | 69.566 |
| hand_open_wide_R | Thumb | -12.463, -66.032, 6.414 | 67.504 | -12.463, -66.032, -8.730 | 67.763 | 26.268 |

### Wrist and body motion

| Clip | Wrist translation (mm) | Wrist rotation (deg) | Max outside-hand motion from rest (mm) | Outside-hand difference vs same pose on master (m) |
| --- | --- | --- | --- | --- |
| hand_fist_L | 3e-05 | 0.0 | 7e-05 | 6.68738897e-08 |
| hand_open_relaxed_L | 3e-05 | 0.0 | 7e-05 | 6.68738897e-08 |
| hand_point_L | 3e-05 | 0.0 | 7e-05 | 6.68738897e-08 |
| hand_thumbs_up_L | 3e-05 | 0.0 | 7e-05 | 2.40274005e-07 |
| hand_peace_L | 3e-05 | 0.0 | 7e-05 | 6.68738897e-08 |
| hand_ok_L | 3e-05 | 0.0 | 7e-05 | 6.68738897e-08 |
| hand_grip_small_L | 3e-05 | 0.0 | 7e-05 | 6.68738897e-08 |
| hand_pinch_L | 3e-05 | 0.0 | 7e-05 | 6.68738897e-08 |
| hand_open_wide_L | 3e-05 | 0.0 | 7e-05 | 6.68738897e-08 |
| hand_fist_R | 3e-05 | 0.0 | 7e-05 | 6.68738897e-08 |
| hand_open_relaxed_R | 3e-05 | 0.0 | 7e-05 | 6.68738897e-08 |
| hand_point_R | 3e-05 | 0.0 | 7e-05 | 6.68738897e-08 |
| hand_thumbs_up_R | 3e-05 | 0.0 | 7e-05 | 2.40050087e-07 |
| hand_peace_R | 3e-05 | 0.0 | 7e-05 | 6.68738897e-08 |
| hand_ok_R | 3e-05 | 0.0 | 7e-05 | 6.68738897e-08 |
| hand_grip_small_R | 3e-05 | 0.0 | 7e-05 | 6.68738897e-08 |
| hand_pinch_R | 3e-05 | 0.0 | 7e-05 | 6.68738897e-08 |
| hand_open_wide_R | 3e-05 | 0.0 | 7e-05 | 6.68738897e-08 |

## Rebuild and apply

The JSON is the editable pose source. Run the guarded wrapper from this directory. It invokes the requested macOS binary with the supplied guard and directs working files into this directory.

```sh
./run_blender.sh build_hands.py
./run_blender.sh hand_check.py --render
./run_blender.sh build_hands.py --embed-previews
./run_blender.sh hand_check.py --render > hand_check.log
python3 contact_sheet.py  # Use an existing local Pillow installation.
```

To apply a Blender Action after importing both GLBs, assign the action to the armature driving Base_Body and select the matching slot. The verifier exercises this path for all 18 actions.

```python
arm = bpy.data.objects['Armature']
action = bpy.data.actions['hand_ok_L']
anim = arm.animation_data_create()
anim.action = action
anim.action_slot = action.slots[0]
bpy.context.scene.frame_set(1)
```

## Visual review and limits

Both hands were inspected in all 54 Cycles CPU views and reviewed independently. The thumbs-up palmar and dorsal cameras are oblique to show both the surface and the thumb height. In the final comparison the thumb clears the folded fingers in all three views. Pinch holds the other fingers closer to the palm, and OK leaves them extended. The small grip has enough room on the palm side for a light grasp. The fist retains a small triangular opening in profile, and full-resolution close-ups show some faceting on the bent knuckles. These are stylised, single-frame poses. Transitions between poses have not been collision-tested.

## Further measurements

| Measure | Left | Right |
| --- | --- | --- |
| Fist thumb cap to skin of folded fingers (mm) | 0.0128 | 0.0462 |
| Thumbs-up thumb elevation above horizontal (degrees) | 50.702 | 45.079 |

### Rest axes by bone

Each vector gives the local positive axis expressed in Blender world coordinates. Each row is one joint in the unchanged Mixamo hierarchy.

| Side | Digit and segment | Local X | Local Y | Local Z |
| --- | --- | --- | --- | --- |
| L | Index1 | 0.13284, 0.99114, 0.00000 | 0.98566, -0.13211, 0.10494 | 0.10401, -0.01394, -0.99448 |
| L | Index2 | 0.13284, 0.99114, 0.00000 | 0.98566, -0.13211, 0.10494 | 0.10401, -0.01394, -0.99448 |
| L | Index3 | 0.13284, 0.99114, 0.00000 | 0.98566, -0.13211, 0.10494 | 0.10401, -0.01394, -0.99448 |
| L | Index4 | 0.13284, 0.99114, -0.00000 | 0.99053, -0.13276, -0.03510 | -0.03479, 0.00466, -0.99938 |
| L | Middle1 | 0.04425, 0.99902, 0.00000 | 0.99748, -0.04418, 0.05559 | 0.05554, -0.00246, -0.99845 |
| L | Middle2 | 0.04425, 0.99902, 0.00000 | 0.99748, -0.04418, 0.05559 | 0.05554, -0.00246, -0.99845 |
| L | Middle3 | 0.04425, 0.99902, 0.00000 | 0.99748, -0.04418, 0.05559 | 0.05554, -0.00246, -0.99845 |
| L | Middle4 | 0.04425, 0.99902, -0.00000 | 0.99841, -0.04422, -0.03492 | -0.03489, 0.00155, -0.99939 |
| L | Ring1 | -0.04425, 0.99902, 0.00000 | 0.99802, 0.04420, 0.04477 | 0.04472, 0.00198, -0.99900 |
| L | Ring2 | -0.04425, 0.99902, 0.00000 | 0.99802, 0.04420, 0.04477 | 0.04472, 0.00198, -0.99900 |
| L | Ring3 | -0.04425, 0.99902, -0.00000 | 0.99802, 0.04420, 0.04477 | 0.04472, 0.00198, -0.99900 |
| L | Ring4 | -0.04425, 0.99902, -0.00000 | 0.99841, 0.04422, -0.03492 | -0.03489, -0.00155, -0.99939 |
| L | Pinky1 | -0.13284, 0.99114, -0.00000 | 0.98985, 0.13267, 0.05095 | 0.05050, 0.00677, -0.99870 |
| L | Pinky2 | -0.13284, 0.99114, -0.00000 | 0.98985, 0.13267, 0.05095 | 0.05050, 0.00677, -0.99870 |
| L | Pinky3 | -0.13284, 0.99114, -0.00000 | 0.98985, 0.13267, 0.05095 | 0.05050, 0.00677, -0.99870 |
| L | Pinky4 | -0.13284, 0.99114, -0.00000 | 0.99053, 0.13276, -0.03510 | -0.03479, -0.00466, -0.99938 |
| L | Thumb1 | 0.21636, 0.42421, 0.87934 | 0.58028, -0.78019, 0.23360 | 0.78515, 0.45973, -0.41497 |
| L | Thumb2 | 0.46454, 0.02374, 0.88523 | 0.63722, -0.70312, -0.31554 | 0.61494, 0.71067, -0.34176 |
| L | Thumb3 | 0.44987, 0.05328, 0.89150 | 0.69325, -0.65016, -0.31097 | 0.56305, 0.75793, -0.32942 |
| L | Thumb4 | 0.41879, 0.11255, 0.90108 | 0.72583, -0.63779, -0.25767 | 0.54570, 0.76194, -0.34879 |
| R | Index1 | 0.13284, -0.99114, 0.00000 | -0.98009, -0.13136, 0.14890 | -0.14758, -0.01978, -0.98885 |
| R | Index2 | 0.13284, -0.99114, -0.00000 | -0.98009, -0.13136, 0.14890 | -0.14758, -0.01978, -0.98885 |
| R | Index3 | 0.13284, -0.99114, -0.00000 | -0.98009, -0.13136, 0.14891 | -0.14759, -0.01978, -0.98885 |
| R | Index4 | 0.13284, -0.99114, -0.00000 | -0.99053, -0.13276, -0.03510 | 0.03479, 0.00466, -0.99938 |
| R | Middle1 | 0.04425, -0.99902, -0.00000 | -0.99318, -0.04399, 0.10795 | -0.10784, -0.00478, -0.99416 |
| R | Middle2 | 0.04425, -0.99902, -0.00000 | -0.99318, -0.04399, 0.10795 | -0.10784, -0.00478, -0.99416 |
| R | Middle3 | 0.04425, -0.99902, 0.00000 | -0.99318, -0.04399, 0.10795 | -0.10784, -0.00478, -0.99416 |
| R | Middle4 | 0.04425, -0.99902, 0.00000 | -0.99841, -0.04422, -0.03492 | 0.03489, 0.00155, -0.99939 |
| R | Ring1 | -0.04425, -0.99902, 0.00000 | -0.99705, 0.04416, 0.06271 | -0.06265, 0.00277, -0.99803 |
| R | Ring2 | -0.04425, -0.99902, -0.00000 | -0.99705, 0.04416, 0.06271 | -0.06265, 0.00277, -0.99803 |
| R | Ring3 | -0.04425, -0.99902, -0.00000 | -0.99705, 0.04416, 0.06271 | -0.06265, 0.00277, -0.99803 |
| R | Ring4 | -0.04425, -0.99902, 0.00000 | -0.99841, 0.04422, -0.03492 | 0.03489, -0.00155, -0.99939 |
| R | Pinky1 | -0.13284, -0.99114, 0.00000 | -0.98759, 0.13237, 0.08451 | -0.08376, 0.01123, -0.99642 |
| R | Pinky2 | -0.13284, -0.99114, -0.00000 | -0.98759, 0.13237, 0.08451 | -0.08376, 0.01123, -0.99642 |
| R | Pinky3 | -0.13284, -0.99114, -0.00000 | -0.98759, 0.13237, 0.08451 | -0.08376, 0.01123, -0.99642 |
| R | Pinky4 | -0.13284, -0.99114, 0.00000 | -0.99053, 0.13276, -0.03510 | 0.03479, -0.00466, -0.99938 |
| R | Thumb1 | 0.23380, -0.40127, -0.88562 | -0.60835, -0.77091, 0.18869 | -0.75845, 0.49465, -0.42435 |
| R | Thumb2 | 0.42391, -0.10306, -0.89982 | -0.62960, -0.74773, -0.21097 | -0.65108, 0.65596, -0.38186 |
| R | Thumb3 | 0.50607, 0.06652, -0.85992 | -0.65027, -0.62556, -0.43108 | -0.56661, 0.77733, -0.27332 |
| R | Thumb4 | 0.47512, -0.00176, -0.87992 | -0.72238, -0.57177, -0.38891 | -0.50243, 0.82041, -0.27293 |

## File identity

| File | SHA-256 |
| --- | --- |
| Read-only master | 0339318b375836ab8891e49bda178da7e6f115e012e83385d9f8850949a7bd6f |
| hands_gestures.blend | e2bb8187d2f4148dccde9503d71ceae39710a3ea4533674e7a1259d5c172a57c |
| base_body.glb | f6a979565d81171a1606a37776e755192744ec1415a8b65e6e68ee537824453f |
| hand_gestures.glb | 022ac7544e0e22f8082caa3a86407c3e2de2052db34d614c87cfede6ddf012ae |
| hand_gestures.json | 5873a4d0847c3c4a09516dce7d4e8a48d4378516e19f4101a6f10b135f5d1f9a |

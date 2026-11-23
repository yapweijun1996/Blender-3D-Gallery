# Studio bomber jacket · round 2

The final candidate passes both checks in the T-pose. The seven motion clips still have collision residuals. The zero-poke-through gate remains open.

## Export and inputs

- [jacket_v2.glb](jacket_v2.glb) is 3,752,652 bytes with 4,882 triangles, 5,260 exported vertices, one skinned garment mesh, 65 master joints, at most 4 normalized influences per vertex and zero embedded animations.
- [jacket_v2.blend](jacket_v2.blend) is 4,594,808 bytes. It contains the editable garment, master rig and hidden body reference.
- The Tripo material settings and all three 1024 × 1024 images match round 1 byte for byte in the export. The editable mesh has 14,646 UV loop coordinates identical to round 1.
- Khronos glTF Validator 2.0.0-dev.3.10 reported 0 errors and 0 warnings. [Validator report](gltf_validator.json) · [Export structure](export_check.json)
- GLB SHA-256 `5b47594d616e9b8558b0c0772c0c04717fc3fedc8871527d63dd8daab5e77dca`.

## Vertex RESULT

The supplied vertex checker samples twelve times per clip. Its minimum column measures signed vertex distance. [RESULT output](motion_check.txt) · [JSON](motion_check.json)

| Clip | Max vertices inside | Min signed distance (mm) |
| --- | ---: | ---: |
| rest | 0 | +1.801 |
| walk | 201 | -18.400 |
| run | 140 | -15.300 |
| wave | 82 | -8.900 |
| jump | 108 | -8.500 |
| idle | 104 | -8.700 |
| nod | 97 | -9.000 |
| dance | 28 | -7.400 |

## Triangle RESULT

The supplied triangle checker samples every third integer frame. Its minimum column measures signed vertex distance. [RESULT output](motion_check_tri.txt) · [JSON](motion_check_tri.json)

| Clip | Max overlapping pairs | Min signed distance (mm) |
| --- | ---: | ---: |
| rest | 0 | +1.801 |
| walk | 808 | -16.600 |
| run | 621 | -15.300 |
| wave | 473 | -8.800 |
| jump | 506 | -8.800 |
| idle | 499 | -8.900 |
| nod | 486 | -8.800 |
| dance | 170 | -7.400 |

## Independent half-frame sweep of 824 poses

The original master and quaternion clips drive the reimported GLB. The measurements include both endpoints and every half frame. Counts are maxima at a single pose. The vertex minimum and pair maximum can occur at different poses.

| Clip | Poses | Max vertices inside | Min vertex mm | Min vertex f | Max pairs | Max pair f | Poses with pairs |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| rest | 1 | 0 | +1.801 | 1 | 0 | — | 0 |
| walk | 113 | 223 | -19.532 | 47.5 | 861 | 39 | 113 |
| run | 61 | 149 | -16.177 | 25.5 | 659 | 8 | 61 |
| wave | 129 | 85 | -9.078 | 17 | 473 | 0 | 129 |
| jump | 101 | 142 | -11.527 | 7.5 | 511 | 4.5 | 64 |
| idle | 177 | 104 | -8.922 | 39 | 499 | 55.5 | 177 |
| nod | 113 | 97 | -9.031 | 14 | 492 | 37 | 113 |
| dance | 129 | 29 | -7.382 | 40 | 176 | 43 | 129 |

The sum over all poses is 326,976 body-to-garment triangle pairs. Round 1 reached 406,134 pairs across the same frames and 4,882 triangles. The count fell 19.5%. The minimum signed vertex distance worsened in wave, jump, idle and nod. 1,419 distinct crossing garment faces have a rest edge over 12 mm and the longest such edge is 39.902 mm. The remaining contacts and long edges are open acceptance items. [Half-frame data](dense_check.json)

## Rest clearance

The table measures nearest oriented body triangle distance in millimetres. UV seams can give coincident exported vertices. The Euclidean column measures straight-line point-to-surface distance.

| Region | Vertices | Min | P10 | Median | P90 | P95 | Max signed | Max Euclidean |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| all | 5,260 | +1.801 | +5.990 | +11.278 | +20.542 | +24.843 | +29.840 | +29.840 |
| ribbed cuffs | 575 | +2.171 | +3.577 | +9.467 | +12.515 | +13.969 | +23.732 | +23.732 |
| ribbed hem | 577 | +1.801 | +3.869 | +9.547 | +11.826 | +12.687 | +20.473 | +20.473 |
| shoulder and armpit | 458 | +3.539 | +8.949 | +12.372 | +22.297 | +25.276 | +29.840 | +29.840 |
| sleeves | 625 | +2.508 | +3.566 | +9.714 | +15.998 | +17.331 | +23.738 | +23.747 |
| stand collar | 612 | +8.492 | +9.401 | +11.117 | +15.690 | +16.370 | +18.246 | +18.246 |
| torso panels | 2,413 | +3.108 | +9.400 | +13.298 | +24.689 | +27.852 | +29.840 | +29.840 |

The cuffs reach X +269.66 and -269.60 mm. The master wrist coordinates are X +270.90 and −270.42 mm. The ribbed hem spans Z 381.6 to 413.7 mm, near the hips.

The separate 322,212-point rest surface grid had minimum signed clearance +0.669 mm. It found 374 samples above the 30 mm cap. The four affected face zones are below.

| Rest face zone | Samples over 30 mm | Max Euclidean mm |
| --- | ---: | ---: |
| left shoulder and armpit | 1 | +30.033 |
| left torso panels | 203 | +30.692 |
| right shoulder and armpit | 34 | +30.848 |
| right torso panels | 136 | +31.387 |

## Remaining collision and clearance zones

Figures are signed distances in millimetres. Negative values indicate penetration. Triangle depths use a barycentric grid with ten subdivisions on the intersecting faces. The grid measures penetration at sampled points and exact BVH overlap supplies the pair count. Anatomical sides use the character's rest coordinates. The detailed JSON lists every failing pose and nearest body joint. [Zone data](dense_check.json)

| Clip | Garment zone | Failing poses | Max vertices inside | Max pairs | Min vertex mm (frame) | Deepest triangle sample mm (frame) |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| dance | left shoulder and armpit | 60 | 12 | 76 | -7.189 (f52) | -7.717 (f46.5) |
| dance | left sleeves | 2 | 0 | 0 | +0.482 (f40) | — |
| dance | left torso panels | 66 | 18 | 102 | -7.382 (f40) | -7.382 (f40) |
| dance | right shoulder and armpit | 62 | 6 | 38 | -1.292 (f12) | -2.733 (f8) |
| dance | right sleeves | 77 | 0 | 10 | — | -0.542 (f8) |
| dance | right torso panels | 45 | 6 | 11 | -2.532 (f8) | -2.532 (f8) |
| idle | left ribbed cuffs | 177 | 23 | 61 | -3.807 (f6) | -3.933 (f71.5) |
| idle | left ribbed hem | 177 | 17 | 38 | -8.922 (f39) | -9.010 (f18) |
| idle | left shoulder and armpit | 177 | 15 | 110 | -3.642 (f28.5) | -6.032 (f66) |
| idle | left sleeves | 177 | 16 | 75 | -4.897 (f47) | -4.897 (f47) |
| idle | left torso panels | 177 | 31 | 171 | -6.787 (f22) | -7.035 (f28) |
| idle | right shoulder and armpit | 177 | 9 | 39 | -5.958 (f5) | -5.958 (f5) |
| idle | right sleeves | 177 | 0 | 4 | — | -0.078 (f66) |
| idle | right torso panels | 177 | 13 | 24 | -3.506 (f66) | -3.957 (f66) |
| jump | left ribbed cuffs | 50 | 28 | 55 | -5.558 (f42) | -5.881 (f8) |
| jump | left ribbed hem | 50 | 21 | 36 | -9.043 (f40) | -9.158 (f43) |
| jump | left shoulder and armpit | 61 | 20 | 109 | -5.443 (f5) | -8.169 (f5.5) |
| jump | left sleeves | 64 | 23 | 79 | -4.002 (f3.5) | -4.786 (f0) |
| jump | left torso panels | 60 | 44 | 183 | -11.527 (f7.5) | -12.624 (f9) |
| jump | right shoulder and armpit | 56 | 10 | 63 | -5.491 (f41) | -5.662 (f1) |
| jump | right sleeves | 56 | 0 | 4 | — | -0.831 (f9) |
| jump | right torso panels | 54 | 11 | 27 | -5.333 (f6) | -5.373 (f7) |
| nod | left ribbed cuffs | 113 | 13 | 53 | -3.499 (f39) | -4.316 (f17) |
| nod | left ribbed hem | 113 | 19 | 44 | -7.997 (f0) | -7.997 (f0) |
| nod | left shoulder and armpit | 113 | 15 | 101 | -3.516 (f12) | -5.387 (f0) |
| nod | left sleeves | 113 | 13 | 69 | -3.400 (f17) | -4.807 (f23) |
| nod | left torso panels | 113 | 30 | 176 | -9.031 (f14) | -7.444 (f17) |
| nod | right shoulder and armpit | 113 | 6 | 37 | -2.754 (f17) | -5.696 (f40) |
| nod | right sleeves | 113 | 0 | 4 | — | -0.028 (f0) |
| nod | right torso panels | 113 | 8 | 19 | -3.103 (f40) | -3.357 (f17) |
| run | center ribbed hem | 5 | 0 | 4 | — | -0.092 (f10) |
| run | center torso panels | 11 | 1 | 14 | -0.387 (f19) | -2.910 (f2) |
| run | left ribbed cuffs | 13 | 26 | 59 | -2.659 (f29) | -4.537 (f29) |
| run | left ribbed hem | 34 | 13 | 66 | -5.483 (f29) | -6.439 (f23) |
| run | left shoulder and armpit | 53 | 28 | 140 | -15.188 (f10.5) | -12.165 (f24) |
| run | left sleeves | 61 | 21 | 139 | -4.681 (f25) | -5.256 (f11) |
| run | left stand collar | 1 | 1 | 0 | -2.049 (f24.5) | — |
| run | left torso panels | 61 | 89 | 227 | -16.177 (f25.5) | -17.793 (f23) |
| run | right ribbed cuffs | 61 | 6 | 44 | -5.595 (f28) | -5.702 (f28.5) |
| run | right ribbed hem | 25 | 10 | 83 | -7.090 (f3) | -7.703 (f5) |
| run | right shoulder and armpit | 61 | 26 | 84 | -7.434 (f11.5) | -7.434 (f11.5) |
| run | right sleeves | 57 | 16 | 108 | -2.000 (f6) | -4.870 (f4) |
| run | right stand collar | 1 | 0 | 8 | — | -0.022 (f18) |
| run | right torso panels | 59 | 48 | 225 | -14.304 (f10) | -14.777 (f10) |
| walk | center ribbed hem | 12 | 0 | 8 | — | -0.910 (f22) |
| walk | center torso panels | 39 | 14 | 0 | -13.696 (f35) | — |
| walk | left ribbed cuffs | 113 | 23 | 68 | -17.507 (f14.5) | -14.052 (f56.5) |
| walk | left ribbed hem | 113 | 23 | 35 | -19.532 (f47.5) | -12.349 (f23.5) |
| walk | left shoulder and armpit | 113 | 35 | 123 | -10.668 (f29.5) | -9.817 (f53) |
| walk | left sleeves | 113 | 31 | 118 | -13.747 (f43.5) | -14.019 (f52.5) |
| walk | left torso panels | 113 | 58 | 204 | -18.216 (f2) | -19.264 (f37.5) |
| walk | right ribbed cuffs | 17 | 5 | 13 | -3.447 (f34) | -7.801 (f35) |
| walk | right ribbed hem | 58 | 17 | 29 | -5.818 (f8) | -9.104 (f39) |
| walk | right shoulder and armpit | 113 | 28 | 100 | -8.462 (f42) | -7.417 (f37) |
| walk | right sleeves | 80 | 21 | 85 | -7.801 (f35) | -8.036 (f34.5) |
| walk | right torso panels | 113 | 72 | 237 | -19.066 (f41.5) | -19.066 (f41.5) |
| wave | left ribbed cuffs | 129 | 18 | 56 | -5.388 (f19) | -5.570 (f34.5) |
| wave | left ribbed hem | 129 | 18 | 39 | -9.078 (f17) | -9.078 (f17) |
| wave | left shoulder and armpit | 129 | 9 | 101 | -2.906 (f19) | -5.387 (f0) |
| wave | left sleeves | 129 | 12 | 73 | -3.365 (f19) | -4.842 (f58) |
| wave | left torso panels | 129 | 30 | 175 | -7.952 (f45) | -8.732 (f19) |
| wave | right shoulder and armpit | 20 | 9 | 36 | -5.609 (f0.5) | -5.635 (f0) |
| wave | right sleeves | 51 | 4 | 29 | -0.576 (f19) | -0.875 (f18) |
| wave | right torso panels | 20 | 8 | 17 | -2.991 (f0) | -2.991 (f0) |

## Fit and reproduce

The fitter uses Blender 5.1.2. It starts from the read-only round-1 garment and sweeps the master actions via their Blender 5 action slots. The fit uses worst-pose nearest-surface directions pulled back through the skin matrix, a 2 mm offset target, a 30 mm clearance cap and Laplacian smoothing with a displacement floor. The search tries local topology and shape changes at shoulders, armpits, sleeves and hem, and normalizes local skinning to four influences. The last loft trial rebinds inserted midpoints against the pre-split trajectories.

The initial broad offset, the local shape search and the contact patch search share the sixteen update slots. Candidate selection considers overlap counts, penetrated vertices and depth. The emitted checkpoint retained the original 4,882-triangle topology after the refinements increased the overall collision score. Its largest vertex displacement from round 1 was 11.445 mm. Byte-for-byte reproduction from a fresh build was unverified.

Workbench rendering is skipped by the wrappers. The supplied measurement loops retain their original frame samples and have separate report paths. Blender Cycles CPU renders the reimported final export.

Run from this folder with the supplied guarded Blender executable, with `BLENDER` set to its path and `DYLD_INSERT_LIBRARIES` exported to the supplied guard.

```sh
"$BLENDER" -b -noaudio --python-exit-code 1 --python fit_jacket_r2.py
"$BLENDER" -b -noaudio --python-exit-code 1 --python fit_jacket_r2.py -- --checkers
"$BLENDER" -b -noaudio --python-exit-code 1 --python fit_jacket_r2.py -- --verify
"$BLENDER" -b -noaudio --python-exit-code 1 --python fit_jacket_r2.py -- --renders
```

## Renders and provenance

The six-view sheet shows front, rear and left profile on the top row and right profile, three-quarter and jacket-only on the bottom. Each motion render shows the minimum signed vertex-distance frame found by the dense checker.

An independent visual review confirmed the short stand collar, wrist-length cuffs, hip-height ribbed hem and loose, tapered silhouette. The olive material, zipper, raglan seams and ribbing still read as the round-1 design. The rear collar corners flare slightly, the side hem is wavy and the pocket welts have uneven recesses. The reviewer observed skin slits above the viewer-right pocket in walk 47.5 and patches below the sleeve and across the chest in run 25.5. Wave 17 and jump 7.5 show severe folds. The available angles leave the occluded surfaces unobserved.

| Render | Frame | SHA-256 |
| --- | ---: | --- |
| [six_view.png](six_view.png) | 1 | `e48c8728d5b8e8bff1bf979baee2d0bbcdcf7ffd8bc8fc912c8cda296126de15` |
| [walk.png](walk.png) | 47.5 | `6b29408d103b54655cb4ac20c712cf13157b50fd8c6e4840fc30248167eb058b` |
| [run.png](run.png) | 25.5 | `428947465b323ca098847786caa2aaae6909537abbca30fb2b803d29ea9b53b1` |
| [wave.png](wave.png) | 17 | `4e8e9caa203f72b6d93a081d2ccd270c70d2f7eb64a4a51946d4cadae93ee235` |
| [jump.png](jump.png) | 7.5 | `b4783989acd32bc77d268a70d6552c6866139c5fa2ab7d930c40144379659eef` |

| Input or evidence | SHA-256 |
| --- | --- |
| Round-1 editable source | `2353d2d7300352c214ea7ddc9a4668ebde68c17aafa2380af72940036ecb25b1` |
| Round-1 signed module | `fca866a625a82f969fa0aa20c633ab6228c307530bfc93adf0d3fe196e812677` |
| Tripo retopology source | `9150874a867112b4db7e553f3d46343edb48b26fc8da19a274b7ad1ccb8d97d1` |
| Master body and rig | `0339318b375836ab8891e49bda178da7e6f115e012e83385d9f8850949a7bd6f` |
| Motion source | `ffccda1ba2a50eb10948853e03d17f0d095cd9b953d644c03c4fb9cb95529410` |
| Round-2 fitter | `b570bf86adec847c345bd1da77ba04bf8f0a67300890a438a7a3d76c39a79ac1` |
| Round-2 editable source | `a702b42813ae87ca0b80c2a44eb9fe0420c2261fa3bd6084a97cc683ba0dca70` |
| Dense check | `ac999e407dc32331c1ae4de5b1faa4d92d14d14d558a2cafb081b416061bf190` |

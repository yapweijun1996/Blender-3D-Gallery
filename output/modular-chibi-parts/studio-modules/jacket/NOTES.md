# Olive bomber jacket fit

The delivered v1 is a fitted, skinned candidate. The T-pose passes both collision checks. All seven clips still fail the zero-penetration requirement. The final motion renders show visible body breakthrough.

## Export

- One garment mesh, 4,882 triangles, 5,260 exported vertices and 65 master joint names. At most 4 normalized influences per vertex.
- GLB 3,752,652 bytes. Editable BLEND 4,594,835 bytes. The GLB has no animation tracks. The BLEND contains the master armature and a hidden Base_Body fit reference.
- The original UV map and Tripo material are retained. Base color, normal and roughness/metallic are embedded at 1024 × 1024.
- Khronos glTF Validator 2.0.0-dev.3.10 reported 0 errors and 0 warnings.
- GLB SHA-256 `fca866a625a82f969fa0aa20c633ab6228c307530bfc93adf0d3fe196e812677`.

## Supplied vertex RESULT

The supplied vertex checker reports the largest per-frame count at twelve sample times per clip. Motion distances inherit its original rounding.

| Clip | Inside vertices | Minimum signed distance (mm) |
| --- | ---: | ---: |
| rest | 0 | +1.732 |
| walk | 188 | -20.400 |
| run | 175 | -16.800 |
| wave | 74 | -7.300 |
| jump | 103 | -8.700 |
| idle | 91 | -6.800 |
| nod | 95 | -5.300 |
| dance | 23 | -8.700 |

## Supplied triangle RESULT

The supplied triangle checker reports the largest count of body-to-garment triangle pairs sampled every third integer frame. Its distance column measures garment vertices.

| Clip | Overlapping pairs | Minimum signed distance (mm) |
| --- | ---: | ---: |
| rest | 0 | +1.732 |
| walk | 882 | -20.200 |
| run | 744 | -16.700 |
| wave | 582 | -7.700 |
| jump | 630 | -9.700 |
| idle | 606 | -7.000 |
| nod | 592 | -5.300 |
| dance | 221 | -8.700 |

## Half-frame sweep

The GLB was reimported against the original master and measured at 824 poses, including both clip endpoints, every half frame and all sample times from the supplied checkers. Counts and minima can occur at different frames.

| Clip | Poses | Inside vertices | Minimum signed distance (mm) | Vertex frame | Triangle pairs | Pair frame |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| rest | 1 | 0 | +1.732 | 1 | 0 | — |
| walk | 113 | 205 | -21.160 | 33.5 | 887 | 39.0 |
| run | 61 | 175 | -20.266 | 23 | 778 | 10.5 |
| wave | 129 | 77 | -7.813 | 13 | 587 | 0.5 |
| jump | 101 | 111 | -9.702 | 9 | 630 | 42.0 |
| idle | 177 | 91 | -7.052 | 12.5 | 606 | 64.0 |
| nod | 113 | 97 | -5.333 | 0 | 592 | 18.0 |
| dance | 129 | 24 | -8.676 | 40 | 222 | 42.5 |

## Rest clearance

These statistics use the signed distance to the nearest oriented body triangle after GLB reimport. At UV seams the exported garment can have multiple vertices with the same position.

| Region | Vertices | Min (mm) | P10 | Median | P90 | P95 | Max |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| all | 5,260 | +1.732 | +5.688 | +11.118 | +19.749 | +24.181 | +29.650 |
| ribbed cuffs | 576 | +1.793 | +2.796 | +9.463 | +12.186 | +13.884 | +19.732 |
| ribbed hem | 577 | +2.100 | +3.011 | +9.479 | +11.523 | +12.090 | +16.631 |
| shoulder and armpit | 455 | +3.584 | +8.295 | +11.880 | +20.576 | +23.891 | +27.147 |
| sleeves | 622 | +2.099 | +2.786 | +9.477 | +15.409 | +16.920 | +22.438 |
| stand collar | 611 | +8.350 | +9.401 | +11.072 | +15.694 | +16.370 | +18.246 |
| torso panels | 2,419 | +1.732 | +9.400 | +13.251 | +24.206 | +27.148 | +29.650 |

The cuff ends reach X = +269.600 and -269.600 mm. The corresponding wrist joints sit at X = +270.898 and −270.421 mm. The classified ribbed hem spans Z = 379.9–413.6 mm. The hip joint is at Z = 372.9 mm. The maximum Euclidean rest distance is 29.650 mm.

## Residuals

The nearest body joint is the dominant influence on the nearest body face. Triangle interior witness depths are measured on a barycentric grid. The complete failing frame list and the worst vertex by clip, region and body joint are in [dense_check.json](dense_check.json).

| Clip | Frame | Garment region | Nearest body joint | Deepest vertex (mm) | Deepest sampled face interior (mm) | Face frame |
| --- | ---: | --- | --- | ---: | ---: | ---: |
| walk | 33.5 | Left torso panels | `mixamorig:LeftForeArm` | -21.160 | -19.299 | 13.0 |
| run | 23 | Left torso panels | `mixamorig:LeftForeArm` | -20.266 | -17.124 | 10.0 |
| wave | 13 | Left ribbed hem | `mixamorig:LeftForeArm` | -7.813 | -7.611 | 40.5 |
| jump | 9 | Left torso panels | `mixamorig:LeftForeArm` | -9.702 | -10.700 | 9.0 |
| idle | 12.5 | Left ribbed hem | `mixamorig:LeftForeArm` | -7.052 | -7.467 | 22.0 |
| nod | 0 | Left ribbed hem | `mixamorig:LeftForeArm` | -5.333 | -5.503 | 0.0 |
| dance | 40 | Left torso panels | `mixamorig:Spine1` | -8.676 | -8.016 | 43.5 |

The unmodified body also registers forearm/hand versus lower-body intersections. For example, the left arm reaches 233 triangle pairs with the lower body at walk frame 54.5, and the right arm reaches 175 at run frame 0. The supplied rig and clips were used as inputs. [Body contact measurements](work/master_contacts.json)

## Visual review

The author and an independent reviewer inspected all ten PNGs for this exact export. The olive material, zipper, ribbing, wrist coverage and static neck and hem coverage passed visual inspection. The UV-guided rest smoothing straightened the pocket welts and softened large creases. The rest views still show a recessed pocket welt, an uneven collar rim, a creased cuff and an asymmetric ribbed hem. The profile and garment-only views expose these features.

Walk 23 shows exposure above a pocket and at the opposite hem. Run 12 shows exposed skin under the extended arm at the side panel and small slivers behind the raised cuff. Wave 25 shows a short skin slit beneath the raised sleeve. Jump 20 shows visible pocket and hem creasing. The photographed angle leaves possible breakthrough on occluded surfaces unverified.

The six rest views and four posed views use Cycles CPU at 12 samples. Walk, run, wave and jump use the supplied checkers’ preview frame at 40% of each clip. [Render manifest](renders/manifest.json)

| Motion PNG | Frame |
| --- | ---: |
| [walk](renders/walk.png) | 23 |
| [run](renders/run.png) | 12 |
| [wave](renders/wave.png) | 25 |
| [jump](renders/jump.png) | 20 |

## Fit and reproduction

The source zipper faces Blender −Y and the garment is Z-up after glTF import. The fitter welds coincident UV-split positions while preserving loop UVs and removes recessed lining at the collar, cuffs and hem. It maps the torso and sleeves to the master, transfers nearest-face barycentric skin weights and smooths the joint transitions before keeping four normalized influences.

The bake samples the seven quaternion clips using their Blender 5 action slots. It uses a 2.05 mm target margin and a 30 mm rest clearance cap. It fits the worst sampled vertex distances, adds constraints from intersecting triangle interiors, and splits long edges on intersecting triangles. The final release also smooths local rest displacements against the source UV correspondence, clamps Euclidean rest clearance, and sets the cuff reach within 270 mm.

The chosen search recorded 13 scans including the baseline and used at most 12 update slots. The fitting order and candidate selection are deterministic on the supplied inputs. A second full rebuild was not compared byte for byte. Two exports from the same fitted checkpoint matched byte for byte. [Fit history](work/solve_report.json)

Workbench aborted with exit 134 when run in background mode. The wrapper executes both supplied measurement paths using their original sampling and writes distinct report names. It skips their Workbench calls because the image set is rendered from the verified export with Cycles CPU.

Use the supplied Blender 5.1.2 executable and `DYLD_INSERT_LIBRARIES` guard from this directory.

```sh
"$BLENDER" -b -noaudio --python-exit-code 1 --python fit_jacket.py
"$BLENDER" -b -noaudio --python-exit-code 1 --python fit_jacket.py -- --checkers
"$BLENDER" -b -noaudio --python-exit-code 1 --python fit_jacket.py -- --verify
"$BLENDER" -b -noaudio --python-exit-code 1 --python fit_jacket.py -- --renders
```

## Evidence

| File | SHA-256 |
| --- | --- |
| [source_studio_retopo.glb](source_studio_retopo.glb) | `9150874a867112b4db7e553f3d46343edb48b26fc8da19a274b7ad1ccb8d97d1` |
| [GJH_Chibi_Master_rigged.blend](../../master/GJH_Chibi_Master_rigged.blend) | `0339318b375836ab8891e49bda178da7e6f115e012e83385d9f8850949a7bd6f` |
| [motion.glb](../../../../models/tripo-chibi-motion/motion.glb) | `ffccda1ba2a50eb10948853e03d17f0d095cd9b953d644c03c4fb9cb95529410` |
| [top-03-jacket-tpose.png](../../generated2/top-03-jacket-tpose.png) | `0f95cd8afd8752c18d54a5b794627ae8276ea8ee28ee58274ed953c51510b18c` |
| [fit_jacket.py](fit_jacket.py) | `432dbf6b0c73afba863cb7168a125da62a6ed436e5fc05bd8364981b8a5f079e` |
| [jacket_v1.blend](jacket_v1.blend) | `2353d2d7300352c214ea7ddc9a4668ebde68c17aafa2380af72940036ecb25b1` |
| [motion_check.txt](motion_check.txt) | `b10648f7123839fd5955b2296a034d8784c41b3c96db3c836f99eb39f1e051c6` |
| [motion_check_tri.txt](motion_check_tri.txt) | `40b9754619708c216112b35cdc0bc2904b14647424800df2b00693c2fc0a3987` |
| [dense_check.json](dense_check.json) | `5dc364974855edf029d5a55a533ea692aac715614418d9a9851fc1b1219f5f6c` |
| [gltf_validator.json](gltf_validator.json) | `eae77cb3c05feba0f73b6c5d38cfede6799bdf7750d7fe9ff4a5e069c180b524` |
| [manifest.json](renders/manifest.json) | `8bf6f4db6debd0b01e5abf602cbe624fbe80f2af9e205fa5bee609af846f6b35` |

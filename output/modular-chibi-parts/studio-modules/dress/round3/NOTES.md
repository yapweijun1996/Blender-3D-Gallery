# Studio A-line dress · Round 3

Both collision checkers report zero at all 824 sampled poses. The 0.5 mm clearance gate remains open for walk.

## Asset

- The GLB has 2,500,412 bytes, 3,844 triangles and 2,756 exported vertices. [Dress GLB](dress_v3.glb)
- The .blend has 9,648,618 bytes and includes the master as a fitting reference. [Editable Blender source](dress_v3.blend)
- The GLB contains 1 skinned garment mesh, 65 joints and 0 animation clips. Maximum influences are 4 with weight sum error ≤ 1.2e-07.
- Round 2 Tripo material definition and all three embedded 1024 × 1024 texture byte sequences match. The UV audit retained 2,592 of 2,592 distinct prior UV coordinates and added 160 interpolated coordinates.
- Khronos glTF Validator 2.0.0-dev.3.10 reports 0 errors and 0 warnings. [Validator output](gltf_validator.json)
- GLB SHA-256 `af27ccd42422478a1199ff97498d33ed37cfe6599666ebd3beb260b55c7e7a4a`.
- Blend SHA-256 `40f9394659448a9ea8bffa776a0c93761dffe8519c4869ba74761287b8e8aedc`.

## Collision RESULT tables

The checkers reimported the GLB and rebound it to the master. Rest and every integer and half frame of all seven actions were measured against the corrected motion asset. The armature retained its existing bone rotation modes and each imported action bound through its action slot. Counts are the maximum in any one sampled pose. The signed clearance is the minimum outward-normal projection from the closest body triangle to a garment vertex. [Corrected motion asset](../../../body-fix/motion_fixed.glb)

### Vertex checker

[RESULT text](motion_check.txt) · [Every sampled pose](motion_check.json)

| Clip | Poses | Max inside vertices | Min signed (mm) |
| --- | ---: | ---: | ---: |
| rest | 1 | 0 | 1.886 |
| walk | 113 | 0 | 0.132 |
| run | 61 | 0 | 0.585 |
| wave | 129 | 0 | 1.182 |
| jump | 101 | 0 | 0.634 |
| idle | 177 | 0 | 1.076 |
| nod | 113 | 0 | 1.182 |
| dance | 129 | 0 | 1.171 |

### Triangle-overlap checker

[RESULT text](motion_check_tri.txt) · [Every sampled pose](motion_check_tri.json)

| Clip | Poses | Max garment/body pairs | Min signed (mm) |
| --- | ---: | ---: | ---: |
| rest | 1 | 0 | 1.886 |
| walk | 113 | 0 | 0.132 |
| run | 61 | 0 | 0.585 |
| wave | 129 | 0 | 1.182 |
| jump | 101 | 0 | 0.634 |
| idle | 177 | 0 | 1.076 |
| nod | 113 | 0 | 1.182 |
| dance | 129 | 0 | 1.171 |

### Remaining clearance shortfalls

| Clip | Failing poses | Garment zone | Closest body zone | Worst frame | Minimum (mm) | Shortfall from 0.5 mm (mm) |
| --- | ---: | --- | --- | ---: | ---: | ---: |
| walk | 72 | shoulder and armpit | Spine1 | 27 | 0.132 | 0.368 |

## Rest clearance

0 exported vertices exceed 30 mm. The additional triangle-center and edge-midpoint probes have 0 below 0.5 mm and 0 above 30 mm. All distances below use mm.

| Zone | Samples | Min | P10 | Median | P90 | P95 | Max |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| all | 2,756 | 1.886 | 6.119 | 14.714 | 24.130 | 25.115 | 29.541 |
| bodice | 510 | 2.819 | 6.004 | 14.570 | 21.376 | 23.024 | 24.673 |
| hem | 560 | 3.043 | 14.847 | 23.135 | 26.173 | 27.301 | 29.541 |
| neck | 398 | 4.583 | 5.246 | 8.907 | 16.470 | 17.896 | 20.595 |
| shoulder and armpit | 229 | 5.032 | 7.421 | 14.575 | 23.077 | 24.325 | 26.758 |
| skirt | 691 | 1.886 | 6.357 | 15.074 | 23.434 | 24.910 | 29.513 |
| sleeve | 368 | 2.123 | 4.646 | 11.327 | 18.524 | 19.712 | 23.087 |
| triangle probes | 15,376 | 1.130 | 5.954 | 14.408 | 23.776 | 24.875 | 29.519 |

The hem's lowest rest point is 33.048 mm above the higher knee. Position-welded geometry has 4 boundary loops and 0 edges shared by more than two faces.

## Master body baseline

Body-only pairs use the master publication's exact-rest-position adjacency filter. Garment/body pairs compare triangles across the two meshes and are listed in the RESULT tables. The neutral baseline has 318 body-only pairs, including 163 eye-to-head, 60 shorts-to-leg, and 95 foot/toe pairs. [Body-fix baseline](../../../body-fix/NOTES.md)

| Clip | Body only, integer occurrences | Body only, half-frame occurrences | Exact integer baseline pair IDs |
| --- | ---: | ---: | --- |
| rest | 318 | 0 | match |
| walk | 28,651 | 28,151 | match |
| run | 17,166 | 16,613 | match |
| wave | 20,540 | 20,222 | match |
| jump | 16,201 | 15,889 | match |
| idle | 28,131 | 27,815 | match |
| nod | 17,994 | 17,681 | match |
| dance | 20,075 | 19,771 | match |

Master SHA-256 `0339318b375836ab8891e49bda178da7e6f115e012e83385d9f8850949a7bd6f`. Corrected motion SHA-256 `3484f5978e94f3e714b320357397d107dd490d56f2eeb64770be292322f9aa2c`. Triangle and vertex minima, garment-to-body region pairs, baseline counts and stage history are in the [dense report](dense_check.json).

## Fitting and reproduction

The repair starts from the Round 2 editable garment and measures the Round 2 export as its baseline. The corrected run baseline reached −9.345 mm and 513 garment/body pairs at the peak sampled pose. The fitter reuses the Round 2 skinning, pose, export and render helpers.

The fitter sampled the worst nearest-surface ray per vertex at half-frame intervals. It formed a 2 mm clearance target with a 30 mm displacement bound and retained the required ray component during the Laplacian spread of the proposal. Sixteen general fit sweeps were followed by local loft work on residual triangles. The two loft passes split 150 edges in contact neighborhoods, increasing the count by 300 triangles. Targeted normalized weights and small local offsets then closed the remaining crossings. Two tapered front-hem controls brought the last face-interior probes into the 30 mm rest limit. Shared motion and master inputs were read from disk.

A checkpoint save after the first loft hit Blender's used-library restriction. The exported checkpoint was reimported, welded at coincident chart vertices and saved to the editable file before continuing. The final material datablock was restored from Round 2. The fit script can rebuild and verify in stages. A byte-identical rebuild of the final artifact was not tested.

Use the guarded Blender 5.1.2 executable and guard library from the task. The following command reruns both checker implementations, the structural and baseline checks, and the Cycles CPU captures on the delivered GLB.

```sh
VECLIB_MAXIMUM_THREADS=1 "$BLENDER" -b -noaudio -t 5 --factory-startup --disable-autoexec \
  --python-exit-code 1 --python fit_dress_r3.py -- check verify render
```

The fit modes are `baseline`, `fit`, `loft`, `finish`, `close`, `clearance`, `anchor` and `trim-rest`. `recover` resumes a partially saved loft from the existing GLB. [Fitting source](fit_dress_r3.py)

## Renders

The six-view sheet shows front, back, left, right, three-quarter and dress only in reading order. The walk, run and jump captures show their minimum-clearance pose. The wave capture shows the raised hand. [Six-view rest sheet](six_view.png)

- [Walk](walk.png), frame 27.
- [Run](run.png), frame 10.
- [Wave](wave.png), frame 19.
- [Jump](jump.png), frame 38.

### Independent visual review

The reviewer matched the GLB hash to the report and inspected the six-view sheet and four motion captures. The pastel pink material, round neckline, short cap sleeves and loose above-knee A-line shape were preserved. The sampled poses showed a continuous dress silhouette. Small puckers remain around the underarm and lower side and back of the skirt. The back hem is slightly scalloped, with a stronger pinch on the right of the sheet than in Round 2. A tiny dark mark at the front neckline is visible in the walk still. Its cause is unconfirmed.

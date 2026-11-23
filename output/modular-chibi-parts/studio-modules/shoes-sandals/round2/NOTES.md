# Sandals v2

All fourteen corrected clips and the rest pose pass both supplied motion checkers. The reimported final GLB passed both measurements on 849 poses, including every frame and half frame of corrected run.

[Lightweight GLB](shoes_sandals_v2.glb) · [Blender source](shoes_sandals_v2.blend) · [Fit script](fit_shoes_v2.py) · [Six-view fit render](fit_views_v2.png) · [Deepest v1 run contact, before and after](run_deepest_v2.png)

## Local run correction

The corrected run produced up to 20 shoe–body triangle overlaps with v1. The most deeply sampled point on an intersecting sandal triangle, at run frame 3, was 0.149 mm inside the body. The closest v1 sandal vertex across the 61 samples was 0.065 mm outside. The before-and-after image uses the same corrected pose and camera on both panels.

The fit takes the v1 GLB as input. It groups split vertices at seams, samples contact depths at all 61 run poses, and maps the nearest body normals back through the skin matrices. For triangle contacts it distributes the correction using the sample’s barycentric coordinates. Required moves target 1.5 mm of clearance and are capped at 20 mm. Each Laplacian pass is projected back onto the sampled clearance constraints. Ankle and toe weight smoothing uses the incident vertices and preserves normalized same-side weights.

The solve moved 9 of 1,731 welded positions by up to 3.138 mm and smoothed the weight transitions at 12 vertices. Index-corresponding face UVs and material settings match v1. The same-camera rest comparison gave a mean absolute RGB difference of 0.51 on the 8-bit scale across 98,280 shared foreground pixels.

[Fit metrics](fit_metrics.json) · [Original run samples](run_v1_half_frames.json) · [Fitted run samples](run_fit_half_frames.json) · [Render manifest](render_manifest.json)

## Motion gate

Both counts are worst-case maxima over the evaluated frames. Signed distance is the minimum sandal vertex distance to the posed body. The threshold is 0.500 mm.

| Pose or clip | Samples | Inside vertices | Body-overlap pairs | Minimum signed distance (mm) | Minimum frame |
| --- | ---: | ---: | ---: | ---: | ---: |
| rest | 1 | 0 | 0 | 2.234 | 1 |
| walk | 57 | 0 | 0 | 1.719 | 22 |
| run | 61 | 0 | 0 | 1.500 | 0 |
| wave | 65 | 0 | 0 | 2.234 | 0 |
| jump | 51 | 0 | 0 | 2.089 | 9 |
| idle | 89 | 0 | 0 | 2.234 | 0 |
| nod | 57 | 0 | 0 | 2.234 | 0 |
| dance | 65 | 0 | 0 | 1.973 | 0 |
| sit_down | 37 | 0 | 0 | 2.351 | 31 |
| sit_idle | 91 | 0 | 0 | 2.351 | 4 |
| stand_up | 31 | 0 | 0 | 2.351 | 25 |
| hold_item | 61 | 0 | 0 | 2.234 | 0 |
| hold_box | 61 | 0 | 0 | 2.234 | 0 |
| hold_bag | 61 | 0 | 0 | 2.234 | 0 |
| take_item | 61 | 0 | 0 | 2.234 | 0 |

[Reimported export results and exact frame data](export_dense.json)

| Supplied checker bank | Vertex checker | Triangle checker |
| --- | --- | --- |
| Seven shared clips | [Log](checks/shared/dense/checker.txt) · [JSON](checks/shared/dense/motion_check.json) | [Log](checks/shared/tri/checker.txt) · [JSON](checks/shared/tri/motion_check.json) |
| Sit and hold item | [Log](checks/actions/dense/checker.txt) · [JSON](checks/actions/dense/motion_check.json) · [Frames](checks/actions/dense/motion_check_frames.json) | [Log](checks/actions/tri/checker.txt) · [JSON](checks/actions/tri/motion_check_tri.json) · [Frames](checks/actions/tri/motion_check_tri_frames.json) |
| Carry clips | [Log](checks/carry/dense/checker.txt) · [JSON](checks/carry/dense/motion_check.json) · [Frames](checks/carry/dense/motion_check_frames.json) | [Log](checks/carry/tri/checker.txt) · [JSON](checks/carry/tri/motion_check_tri.json) · [Frames](checks/carry/tri/motion_check_tri_frames.json) |

The wrapper applies Cycles CPU with a studio world to the supplied preview blocks in memory. Numerical code and sampling stayed as supplied. The shared triangle checker samples every third frame. The separate reimport sweep measures both checks at every sampled frame in the table.

## Asset budget

| Measure | V2 | Limit |
| --- | ---: | ---: |
| Triangles | 3,482 | 3,500 |
| GLB bytes | 1,248,908 | 1,258,291 |
| Blender bytes | 1,244,688 | — |
| Joints | 65 | 65 |
| Maximum influences | 3 | 4 |
| Meshes / embedded animations | 1 / 0 | 1 / 0 |
| Base color / normal / metallic-roughness | 1024 / 512 / 512 px | 1024 px each |
| Khronos errors / warnings | 0 / 0 | 0 / 0 |

GLB size fell from 3,303,896 to 1,248,908 bytes. The 1024 px base-color JPEG is byte-for-byte identical to v1. The normal and metallic-roughness maps use 512 px RGB PNGs. Joint order and inverse bind matrices match v1. The Blender source reopened with one skinned mesh and three packed maps.

[Asset contract](asset_contract.json) · [Khronos validator output](validator.json)

## Remaining geometry

The rest tread reaches Z = -13.000 mm. The rest sandal shells have 0 open edges and 0 nonmanifold edges after position welding. The nonadjacent sandal self-overlap count is 663 pairs, up from 649 in v1. Side renders still show the original folded buckle and strap edges.

[Rest surface measurements](rest_surface.json)

## Rebuild offline

Run from this directory with the supplied guarded Blender 5.1.2 launcher and the repository’s installed Node validator.

~~~zsh
mkdir -p .tmp
export BLENDER_USER_RESOURCES="$PWD/.tmp" BLENDER_USER_CONFIG="$PWD/.tmp"
export TMPDIR="$PWD/.tmp" PYTHONDONTWRITEBYTECODE=1
zsh ../work/run_blender.zsh -t 5 --python fit_shoes_v2.py
node audit_glb.cjs
for bank in shared actions carry; do
  for checker in dense tri; do
    zsh ../work/run_blender.zsh -t 3 --python verify_shoes_v2.py -- "$bank" "$checker"
  done
done
zsh ../work/run_blender.zsh -t 3 --python verify_shoes_v2.py -- dense
zsh ../work/run_blender.zsh -t 2 --python verify_shoes_v2.py -- surface
zsh ../work/run_blender.zsh -t 5 --python render_shoes_v2.py
~~~

Final GLB SHA-256 is `d24dc7ead001090a25c104da2054079adbc795ba5ee1292c5a57aa9fc0e8839d`.

# Round 2 · Boy’s chestnut side-part quiff

The final GLB has **2,988 triangles**, occupies **1,279,224 bytes** and passes both supplied motion checkers. The smallest reported signed distance is **3.5 mm** during run. Khronos glTF Validator 2.0.0-dev.3.10 reported **0 errors and 0 warnings**. An independent image reviewer passed the side-lock ends, temple joins, nape edge and reference hairstyle on the final export.

[Editable Blender scene](hair_sidepart_v2.blend) · [Hair-only GLB](hair_sidepart_v2.glb) · [Rebuild script](fit_hair_r2.py) · [Six views](fit_views_v2.png) · [Left temple](closeup_left.png) · [Nape](closeup_back.png) · [Right temple](closeup_right.png)

## Geometry and material

The round-one editable mesh was already closed, with consistent winding. Its rolled margin, tightly folded side surfaces, near-black source texels and high-metallic material could nevertheless produce chipped tips and dark creases. The v2 script samples the first visible surface along rays from outside the original hair. It builds one continuous exterior across the combed locks and both temples. A periodic hairline follows the ear cutouts and the low rear arc. The nape has dedicated circumferential courses through a rounded cubic profile. The lining joins that profile edge for edge. Angular alignment and surface-interior clearance probes keep long triangles away from the skull.

Both sides share vertices across the centre. The UV chart wraps behind the head and has 16 px of periodic or edge-extended padding. The base colour retains the original sweep with a warm shadow floor and a locally reconstructed right-temple patch. The tangent-space normal map carries the smoothed strand form. On the smooth occiput, normals transition to the fitted dome so individual triangles do not break up the highlight. The final material has two packed 1024 × 1024 PNGs and a metallic factor of 0.30.

Reimporting the GLB and welding attribute duplicates at 0.0000001 m yielded one connected component, zero non-manifold edges, zero inconsistent edge windings and zero intersecting pairs of nonadjacent hair triangles at rest. Exported normals at coincident positions had a maximum vector difference of 0. The master joint hierarchy, order and inverse bind matrices match v1. All 65 joints are present. Only Head and Neck have nonzero weights. The maximum influence count is two, and Neck varies continuously down to the lower rear with a peak of 2.968%. The editable scene was reopened and its hair mesh, armature and packed hair textures were checked. The master body is included in that fitting scene. The GLB contains only the hair mesh and skeleton. [Geometry audit](geometry_check.json) · [Khronos report](khronos_validation.json)

## Motion results

Each checker ran against the final GLB, the requested master and the supplied motion GLB. These are the signed **vertex** distances reported by the scripts. The triangle checker additionally intersects the two triangle meshes. Animated values are rounded by the supplied checkers. The vertex checker samples 12 frames per clip and the triangle checker samples every third integer frame. The pass criterion was 0 inside vertices, 0 overlap pairs and at least 0.0005 m clearance.

### Vertex RESULT

| Clip | Max vertices inside | Minimum signed distance (m) |
| --- | ---: | ---: |
| rest | 0 | 0.004499888 |
| walk | 0 | 0.0042 |
| run | 0 | 0.0035 |
| wave | 0 | 0.0044 |
| jump | 0 | 0.0044 |
| idle | 0 | 0.0044 |
| nod | 0 | 0.0044 |
| dance | 0 | 0.0043 |

[Raw vertex RESULT lines](check_vertex/RESULT.txt) · [Vertex checker JSON](check_vertex/motion_check.json)

### Triangle RESULT

| Clip | Max overlap pairs | Minimum signed distance (m) |
| --- | ---: | ---: |
| rest | 0 | 0.004499888 |
| walk | 0 | 0.0042 |
| run | 0 | 0.0035 |
| wave | 0 | 0.0044 |
| jump | 0 | 0.0044 |
| idle | 0 | 0.0044 |
| nod | 0 | 0.0044 |
| dance | 0 | 0.0043 |

[Raw triangle RESULT lines](check_tri/RESULT.txt) · [Triangle checker JSON](check_tri/motion_check.json)

## Visual measurements

The baseline uses the original 1560 × 1040 fit sheet. The final sheet was rendered from the reimported GLB using the same master, camera directions, target (0, 0, 0.807), 0.55 m orthographic scale, lighting, AgX view transform and Cycles CPU setup at 12 samples with denoising. Each tile is 520 × 520. The final temple and rear closeups render cropped regions at twice that pixel density using the same camera positions and projection.

For each tile and each version, Blender ray tests at pixel centres classified the visible hair against the master body. A hair hit occluded by the head or ear is excluded. Display-space near-black uses 0.2126R + 0.7152G + 0.0722B < 0.12 on normalized, encoded PNG samples. The second measurement linearizes sRGB first and applies the same threshold to relative luminance.

| View | R1 hair px | R2 hair px | R1 near-black | R2 near-black | R1 linear < 12% | R2 linear < 12% |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Front | 70,229 | 69,874 | 19,819 | 678 | 53,681 | 35,583 |
| Three-quarter +X | 82,229 | 81,786 | 20,389 | 494 | 58,155 | 38,388 |
| Three-quarter −X | 83,411 | 83,328 | 24,463 | 1,429 | 60,703 | 44,760 |
| Left +X | 98,899 | 99,039 | 23,490 | 120 | 60,773 | 44,672 |
| Back | 108,139 | 107,908 | 13,004 | 1 | 57,585 | 48,425 |
| Right −X | 101,998 | 102,031 | 32,015 | 1,946 | 72,611 | 58,310 |
| **Total** | **544,905** | **543,966** | **133,180** | **4,668** | **363,508** | **270,138** |

Near-black pixels fell **96.5%** in display space and **25.7%** under linear relative luminance. Visible hair area changed by 0.17%. Both definitions show fewer dark pixels in every individual view. [R1 pixel counts](pixels_v1.json) · [R2 pixel counts](pixels_v2.json)

## Independent visual review

The reference named by round one is the front-facing boy’s side-part in `../../../generated2/hair-04-male-sidepart.png`. The `white-bg/hair-0*.png` files show the bob, spiky and twin-tail variants. The previous fit sheet supplies the side and rear comparison.

| Feature | Final judgment | Evidence |
| --- | --- | --- |
| Side-lock tips | PASS | Both temple tips have a continuous outline and the black chips under the side-facing locks have cleared. |
| Temple-to-cap joins | PASS | Both lock groups meet the cap continuously. The isolated fine slash below the right curl has cleared. |
| Nape | PASS | The rear closeup shows a slim, gently curved edge. The former thick faceted band has cleared. |
| Side-part quiff | PASS | The long raised leftward sweep, off-centre part and short opposing fan remain legible. Rear highlights now run continuously over the dome. |

The final assessment was made by a separate reviewer who saw the six-view sheet, three closeups, original sheet and reference before seeing checker results. The secondary locks read softer and less separated than the reference. The fringe ends are blunter and the top silhouette a little flatter. The nape still has short straight sections under magnification. One pale triangular highlight remains within a lock in the left closeup. The single front reference cannot specify exact side or rear likeness.

## Gate history within this redo

Both supplied checkers ran after every candidate export. One intermediate build had 36 body-overlap pairs although all its vertices cleared the body. Aligning the lower-ring connection by actual azimuth and supporting the interior of long lining triangles resolved it.

| Export SHA-256 prefix | Max inside | Max overlap pairs | Minimum reported distance (mm) |
| --- | ---: | ---: | ---: |
| b8afddf8 | 0 | 0 | 5.1 |
| b8ae3f77 | 0 | 0 | 5.5 |
| b3737298 | 0 | 36 | 3.0 |
| f5ea36e0 | 0 | 0 | 3.5 |
| **b012f663** | **0** | **0** | **3.5** |

## Reproduce locally

Run the following from this directory with the supplied guarded Blender 5.1.2 runtime and the repository’s installed offline Khronos validator. The default Blender script stages are baseline, build, vertex, tri, audit, views and closeups. Individual stages can be selected after `--`. For checker frames, a persistent Blender callback selects the project’s Cycles CPU fallback when the original headless Workbench still renderer starts. The original checker files, poses, frame sampling, distances and collision measurements run unchanged.

```sh
runtime=/private/tmp/claude-501/-Users-yapweijun--claude-spares-spare-Iu3lC0/26a84d71-25c7-41e6-b903-49317aeebb05/scratchpad/modular
mkdir -p .scratch
export TMPDIR="$PWD/.scratch" BLENDER_USER_RESOURCES="$PWD/.scratch/blender"
export PYTHONDONTWRITEBYTECODE=1 DYLD_INSERT_LIBRARIES="$runtime/guard.dylib"
"$runtime/B/Blender.app/Contents/MacOS/Blender" -b -noaudio -t 5 --python-exit-code 1 --python fit_hair_r2.py
```

## Artifact identity

| File | Bytes | SHA-256 |
| --- | ---: | --- |
| `hair_sidepart_v2.glb` | 1,279,224 | `b012f66308ce26fa052c7ec217eed43391092e0c40f7b7fd5ea96ff9c1365db5` |
| `hair_sidepart_v2.blend` | 2,210,023 | `cd02e5e3d7f16b5d57e7273dd37b2f0c174d72295a3adcdc7979540ea4d04782` |
| `fit_hair_r2.py` | 32,117 | `bac1339eeb43549e9890ee74d366e6e3840e228b7138cac2e52cbaf11bbebf69` |
| `fit_views_v2.png` | 2,008,440 | `5da2c685e5f523d0089dcb6ffbfb3acfc6572ac6034ecfb4e7803dac3ab11f94` |
| `closeup_left.png` | 410,220 | `951219d08d41800b1da823abee72398def333f25f8645790a20341dce3974a67` |
| `closeup_back.png` | 153,117 | `ab9addfc0b53e3491a92e40b056ecbaed04a298b934b38622b34b1557053f52c` |
| `closeup_right.png` | 479,855 | `16e79a386c9574e6d2a6c18b7efc1df13d3eee86a0147399073b16740b9691ee` |
| `hair_sidepart_v1.glb` | 1,681,712 | `b7a692b7cc2d726dbe469fa70770944649a8511d67a6b37b76b81e6e7903fff1` |
| `fit_views.png` | 2,113,585 | `9df387997dab73ddcac930ec127b842cc42ccc27f36cad08bf1491ae2cab6746` |
| `hair-04-male-sidepart.png` | 355,371 | `40249b24cb40b4aab165960d4a8167b92a5f49903a2b823da304d732ea0bd80f` |

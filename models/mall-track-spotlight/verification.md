# Mall Track Spotlight verification

Verified on 2026-11-17 with Blender 5.1.2, Node.js 24.21.0, the locked Khronos glTF Validator 2.0.0-dev.3.10 and Three.js 0.187.0. This fixture covers the static Q-BASE row for `MALL-LGT-006`.

## Shipped geometry

| Export | Triangles | Bytes | Width × depth × height |
| --- | ---: | ---: | --- |
| L0, gallery close-up | 11,764 | 417,308 | 360.00 × 208.93 × 270.22 mm |
| L1, mid-distance | 3,000 | 105,184 | 360.00 × 208.88 × 270.17 mm |

Each GLB contains one root, one static mesh and five material primitives. Both are self-contained, use scalar PBR materials and include the warm emissive lens. Both had zero validator errors, warnings and informational messages. A scan of the actual primitive indices and coordinates found zero triangles at or below 10⁻¹² m², and finite positions and unit normals throughout.

The close-up export retains the cooling ribs, hinge scale marks and reflector facets. Its triangle count fits the backlog's 12,000-triangle fixture target. The mid-distance export meets the 3,000-triangle small-prop target. The independent four-view comparison showed coarser reflections on L1 at close range. [Reimported L0 views](reports/reimport-views.webp) · [Mid-distance comparison](reports/lod-comparison.webp)

The first L1 passed the format validator but had three edges shared by four faces on the thin brass bezel trim after welding coincident vertices. Retaining more faces on that trim fixed all three. Both final exports passed the same welded manifold and winding check. On-axis rays reached the emitter in the centre of each optic and the reflector around it.

## Source and mount

The native source reopened with 61 editable meshes. An independent check saved a copy with the tilt axle changed from 126° to 116°, exported its pose and reimported it. All 146 distinct L0 lens vertices followed the predicted rotation within 2.11 × 10⁻⁸ m. The lens centre moved 13.66 mm and all 68 measured upper-rail points stayed fixed. Re-exporting the unedited source with this Blender version reproduced the shipped L0 bytes.

The fit check placed each GLB in the centre of `PANEL_1` from the gallery ceiling kit. Both footprints stayed inside the bay and the top surface at X = −140, 0 and +140 mm met the panel underside at glTF Y = 0.008 m. This measures visual contact for one placement. [Repeat the fit check](verify-fit.mjs)

## Gallery

The production build passed. All 741 unit tests passed. On Chromium with software WebGL, the 1440 × 900, 768 × 1024 and 390 × 844 viewports fetched the same L0 SHA-256 shown below. Each drew 11,764 triangles in five calls per observed frame. Orbit and zoom changed the visible model and reset restored the initial canvas pixels at all three sizes. Touch orbit passed at the phone viewport. Physical phone hardware and sustained frame rate were outside these checks. [Phone viewport capture](reports/gallery-phone-viewport.png)

The Shopping Mall filter and the search term `track spotlight` returned one card on desktop and phone-width layouts. The card decoded a 480 × 400 thumbnail and fetched its GLB on opening. A simulated HTTP 503 displayed the poster and a retry loaded the same validated bytes. [Discovery and recovery evidence](reports/gallery-discovery.json)

The separate repository-wide library suite stopped on its existing `earth` search assertion. That assertion expects two results. The catalog at the preceding commit `a8711762` and the updated catalog both return three, including a condiment set described with earth-tone colours. A separate cross-model lifecycle run timed out tapping Close in the existing Chromium fish sequence before reaching WebKit.

## SHA-256

| File | Digest |
| --- | --- |
| `sources/mall-track-spotlight.blend` | `0e0a1e8d343a4957bfb46313c002945f2d516d5b46f592cca96204635ad2a4b3` |
| `exports/optimized.glb` | `307ce53dc7cf84a24891c735d494f47b4d8f3eed2f56b4c14e614b172fa31348` |
| `exports/lod1.glb` | `6c85a226072c0b325a5c27c1e10ca7f53697b9182aa5bfe3af1e2ccacf7a95b2` |

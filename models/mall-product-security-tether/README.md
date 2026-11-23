# Mall Product Security Tether

Two unbranded satin housings and a curved graphite lead connect a computer shop's display table to a laptop palm rest. Each end has its own flat adhesive sole and molded strain relief. The pale jade insets are fixed visual details. [Studio preview](previews/mall-product-security-tether.jpg) · [Installed on the existing laptop and table](reports/levels-and-installation.jpg)

## Placement

The [main GLB](exports/mall-product-security-tether.glb) uses metres. Its pivot is at the centre of the table foot, +Y points up, and the lead bends toward +Z. Both soles face downward. The smaller sole is 20 mm higher to meet the laptop. The gallery thumbnail includes a studio support under this raised end. The model itself contains just the tether, housings and soles.

| Interface | Local centre X, Y, Z | Contact footprint |
| --- | --- | --- |
| Table adhesive | (0, 0, 0) | Rounded 50 × 50 mm, 9.5 mm corner radius |
| Device adhesive | (−0.150, +0.020, 0) | Rounded 30 × 20 mm, 5 mm corner radius |

Use the [original display table](../tv-demo-table/README.md) as the reference frame. Place the [laptop](../laptop/README.md) at (+0.500, +0.800, +0.240) and the tether at (+0.770, +0.800, +0.320), both at unit scale and zero yaw. The cable rises over the device edge before meeting the sensor. The complete close model spans 193.0 × 67.5 × 29.7 mm in width, depth and height. This exhibit represents the external appearance and installed fit of the fixture.

## Levels and verification

| File | Triangles | Draw calls | Bytes |
| --- | ---: | ---: | ---: |
| [Close](exports/mall-product-security-tether.glb) | 2,648 | 15 | 99,884 |
| [Middle](exports/mall-product-security-tether-lod1.glb) | 1,402 | 6 | 63,584 |
| [Distant](exports/mall-product-security-tether-lod2.glb) | 500 | 2 | 24,792 |

The [Blender source](sources/mall-product-security-tether.blend) contains named editable close-level meshes for each adhesive sole, housing, port sleeve, inlay and cable. The middle level reduces the cable segmentation and groups repeated finishes. The distant level retains both mounting faces and the curved lead in two finishes. None of the three exports needs external textures. [Rights and provenance](LICENSE.md)

Khronos validation recorded zero errors, warnings or informational findings on all three GLBs. The assembly test uses the real tabletop, chassis and moving lid. Eighteen opposing rays at each level measured a maximum 0.000012 mm seating gap. Raising the tether 3 mm failed the contact test. In a 3 mm grid over the laptop, sampled upper surfaces rose at most 9.41 mm above the palm plane. The smallest measured vertical lid gap in this grid was 12.72 mm over 301 poses of the 2.5 s clip. These are sampled geometry measurements. [Table, chassis and lid results](reports/geometry.json)

Blender reopened the three source collections, verified closed consistently oriented meshes and reimported each GLB. Bounds, triangle counts and signed triangle volumes matched. Both a fresh build and a separate export of the saved source reproduced each delivered GLB byte for byte. A Chromium software WebGL render drew every variant and the actual mounted computer. [Source check](reports/source.json) · [Rebuild hashes](reports/rebuild.json) · [Browser verification](reports/browser.json)

## Reproduce

From the Gallery root with Blender 5.1.2, the project's Node dependencies and Playwright Chromium installed:

```sh
asset=models/mall-product-security-tether
blender -b --factory-startup -Y --python-exit-code 1 -P "$asset/generate.py" -- --export-source
blender -b --factory-startup -Y --python-exit-code 1 -P "$asset/inspect_source.py"
node "$asset/verify.mjs"
node "$asset/verify-browser.mjs"
```

A copy of `generate.py` in an empty folder builds the stand-alone asset procedurally. Use `--rebuild` to replace the source intentionally or `--skip-render` to export without rendering the thumbnail.

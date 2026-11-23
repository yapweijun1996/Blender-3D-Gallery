# Mall shop door header · 2 m opening

A 400 mm tall stepped header for the mall's 2 m wall opening and existing [2.10 m glazed double door](../mall-shopfront-door/README.md). The rear infill sits between the wall ends. Its wider front shoulders lap 50 mm onto each return and rest directly over the fixed head of the face-mounted door. Four limestone fascia panels, a dark bronze upper band and a slim champagne line follow the original [wall finishes](../mall-wall-module-2m/README.md). [Studio render](previews/mall-shop-door-header-2m.jpg) · [Installed doorway in Chromium](reports/installed.png)

## Place the header

The bottom-centre pivot lies on the **wall centreline at door-head height**. glTF uses +Y up and +Z outward. Dimensions below are local metres.

| Section | X | Y | Z |
| --- | --- | --- | --- |
| Rear infill inside the clear opening | −1.00 to +1.00 | 0 to 0.40 | −0.075 to +0.075 |
| Wider face over the door frame | −1.05 to +1.05 | 0 to 0.40 | +0.075 to +0.195, including the shallow decorative reveals |

In the six-metre shop layout, place the header at **(0, 2.40, 3.00)** and the unscaled door at **(0, 0, 3.135)**, both with zero yaw. The original fixed door head covers Z = 3.075 to 3.195 and ends at Y = 2.40. The new fascia sits directly on that frame; the top of its rear fill reaches the 2.80 m wall. The fixed-door aperture is 1.94 × 2.32 m. Each operating leaf and its hardware keep their original geometry and pivots.

The west and east sockets sit at local (−1, 0, 0) and (+1, 0, 0). The door-head socket sits at (0, 0, +0.135). Socket names begin with `CONNECTOR_West`, `CONNECTOR_East` and `CONNECTOR_DoorTop` and end with the detail level. The main backing has a stepped plan throughout its height. Applying its maximum 2.10 × 0.27 m rectangle to the rear of the opening would intersect the wall returns.

## Editable geometry and levels

The [Blender source](sources/mall-shop-door-header-2m.blend) contains separate LOD0, LOD1 and LOD2 collections. The close level includes four independently editable, eased panels and a single stepped backing with its front trims. The [original limestone artwork](../mall-wall-module-2m/sources/honed-limestone.png) is packed into the editable source and close GLB. Mid-distance geometry uses flat-faced panels and solid-colour materials. The distant mesh carries the major finish bands in vertex colours.

| Level | Triangles | Draw calls | Bytes |
| --- | ---: | ---: | ---: |
| [Close](exports/mall-shop-door-header-2m.glb) | 396 | 7 | 151,300 |
| [Middle](exports/mall-shop-door-header-2m-lod1.glb) | 204 | 4 | 12,808 |
| [Distant](exports/mall-shop-door-header-2m-lod2.glb) | 92 | 1 | 7,256 |

## Verification

- The three actual GLBs passed Khronos validation with zero errors and warnings. At each level, 90 ray hits compared the existing fixed door head and new soffit; 112 compared the rear insert, front shoulders and both [original corner walls](../mall-wall-corner-2m/README.md). Twelve further checks resolved the stepped plan and top. The largest measured gap between mating planes was 0.106 μm. Raising the header 5 mm or moving it inward 10 mm failed the seat checks. [Assembly test](reports/geometry.json)
- Moving both original door leaves through 0–90° in one-degree steps produced a minimum 100 mm vertical clearance below the header. At full opening the clear width between the two leaf assemblies, including pull hardware, measured 1.734 m. This test covers the complete existing moving geometry and this mounting arrangement. [Door clearance](reports/geometry.json)
- Blender confirmed closed positive-volume source meshes, preserved bounds and volume after reimport, and a packed original texture with a relative path. A fresh procedural build and a re-export of the saved source produced the same three GLBs byte for byte. [Source and reimport](reports/source-reimport.json) · [Rebuild record](reports/rebuild.json)
- Chromium loaded the exact three files, decoded the 512 px image, checked the actual draw counts and rendered the full-detail header with the original wall returns and doorway. The installed image shows both leaves open 45°. [Browser metrics](reports/browser.json)

Original project geometry, materials and renders. The limestone image was created for Blender-3D-Gallery. Public download and redistribution terms are unspecified. This fictional commercial-interior model records visual fit. Structural capacity, fire performance, installation and physical-device performance require their own assessments.

## Reproduce

From the repository root with Blender 5.1.2, the project's Node dependencies and Playwright Chromium:

```sh
asset=models/mall-shop-door-header-2m
blender -b --factory-startup -Y -t 4 --python-exit-code 1 -P "$asset/generate.py" -- --export-source
blender -b --factory-startup -Y -t 2 --python-exit-code 1 -P "$asset/inspect_source.py"
node "$asset/verify.mjs"
node "$asset/verify-browser.mjs"
```

`--export-source` preserves the saved model edits. To build procedurally in a fresh directory, copy `generate.py` there and pass `--texture` with the original wall limestone PNG. Replacing an existing source requires `--rebuild`. Add `--skip-render` for export-only checks.

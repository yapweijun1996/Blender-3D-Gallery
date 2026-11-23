# Mall Cosmetics Tester Bar

A freestanding beauty fixture for the pharmacy and beauty shop. A champagne-framed mirror rises above an ivory counter and a pair of reeded celadon cabinet doors. The lip palette holds three uncapped lipsticks and four colour swatches. The complexion palette holds three pump bottles and four foundation swatches. All sample colours, shapes and finishes were authored for the Gallery. [Studio preview](previews/mall-cosmetics-tester-bar.jpg) · [Actual GLBs in Chromium](reports/levels-and-samples.jpg)

## Placement and inspection

The [main GLB](exports/mall-cosmetics-tester-bar.glb) has a ground-centre pivot, 1.00 m width, 0.80 m depth and 1.50 m height. In glTF, +Y is up and the customer approaches from +Z. The countertop is 0.867 m above the floor. From the customer's side, lip colours are on the left and complexion samples are on the right. Registry entry `MALL-RET-020` covers the overall fixture.

| Inspectable surface | Local position in glTF metres |
| --- | --- |
| Inset silver face | Centre (0, 1.235, −0.2805), facing +Z |
| Four swatches per palette | X offsets −0.144, −0.048, +0.048, +0.144 around centres −0.224 and +0.224. All faces are at Y = 0.8896 and Z = 0.154. |
| Three upright samples per palette | X offsets −0.119, 0, +0.119 around the same centres, at Z = 0.018 |
| Tray and sample seats, close level | The pans and product cases reach the blind-pocket floors at Y = 0.876. The pigments sit on cup bottoms at Y = 0.886. The surrounding tray tops reach Y = 0.893. |

The mirror uses a low-roughness silvered PBR finish. Its appearance follows the viewer's lighting environment. The products and cabinet are static. The fixture height describes this model's geometry. Physical accessibility and installation depend on the surrounding space and equipment.

## Detail levels

The [editable Blender file](sources/mall-cosmetics-tester-bar.blend) contains three collections and a studio outside the GLBs. The close level retains 25 editable meshes, including both pocketed trays, pigment sets, individual products, cabinet fronts and the separate mirror frame and face. The middle level retains the recesses and all six samples, reduces the geometric profiles and batches the cabinet, mirror and sample area. The distant level represents the pans as coloured surfaces and groups the major finishes into three draws. All three use material properties and vertex colours without texture downloads. [Dimensions and export metrics](reports/geometry.json)

| File | Triangles | Draws |
| --- | ---: | ---: |
| [Close](exports/mall-cosmetics-tester-bar.glb) | 10,800 | 39 |
| [Middle](exports/mall-cosmetics-tester-bar-lod1.glb) | 5,936 | 12 |
| [Distant](exports/mall-cosmetics-tester-bar-lod2.glb) | 2,496 | 3 |

## Verification and reproduction

Khronos validated all three delivered GLBs. Triangle ray tests measured the plinth contact, mirror seat, eight pigment-to-cup and cup-to-tray contacts, and six product-to-tray contacts. Lifting the lip pigments 6 mm failed the seat test. Blender reopened the source, checked closed outward-oriented mesh surfaces, and reimported each GLB with the same bounds, triangle count and aggregate signed mesh volume. A separate procedural build and export of the saved source reproduced all three GLBs byte for byte. [Source and reimport](reports/source.json) · [Independent rebuilds](reports/rebuild.json)

Chromium rendered the exact exported bytes under one studio environment, including a closer view of the lipstick and foundation trays. The middle and distant views retained more than 99% silhouette intersection-over-union against the close view from the documented camera. [Software WebGL measurements](reports/browser.json)

From the Gallery repository root with Blender 5.1.2, project Node dependencies and the project's Playwright Chromium installed:

```sh
asset=models/mall-cosmetics-tester-bar
blender -b --factory-startup -Y --python-exit-code 1 -P "$asset/generate.py" -- --export-source
blender -b --factory-startup -Y --python-exit-code 1 -P "$asset/inspect_source.py"
node "$asset/verify.mjs"
node "$asset/verify-browser.mjs"
```

For a clean procedural build, run a copy of `generate.py` in an empty directory. Use `--rebuild` to replace the saved source intentionally. Use `--skip-render` for export-only runs. [Rights and provenance](LICENSE.md)

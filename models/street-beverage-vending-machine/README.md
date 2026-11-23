# Street Beverage Vending Machine

Original, metre-scale static street prop with a warm ivory cabinet, petrol-blue trim, a glazed display, four lit shelves, twenty front facings and twenty reserve cans, selection keys, an inert reader-shaped panel, a recessed pickup chute and ventilated service panels. Generic flavor labels and legends do not represent any real brand.

- `street-beverage-vending-machine.blend` is the editable source with grouped, individually named parts and a studio camera. Front faces Blender −Y; export is glTF +Y up at a floor-level origin.
- `exports/street-beverage-vending-machine.glb` contains only the model. The transparent material is retained; preview camera, lights and floor are not exported.
- `previews/studio.webp` is a 512 px true Blender render of the same geometry. The export batches parts by group and material and omits unused UVs.
- Static visual model only: no vending, payment, prices, animation or game integration. Public redistribution terms are unspecified, so Gallery download is disabled.

## Reproduce and verify

At repository root, with Blender 5.3.0, WebP tools, and the project's locked Node dependencies installed:

```sh
blender -b --python-exit-code 1 --python models/street-beverage-vending-machine/generate.py
cwebp -quiet -resize 512 512 -q 85 models/street-beverage-vending-machine/previews/studio.png -o models/street-beverage-vending-machine/previews/studio.webp
node models/street-beverage-vending-machine/verify.mjs
blender -b --python-exit-code 1 --python models/street-beverage-vending-machine/verify_blender.py -- models/street-beverage-vending-machine/exports/street-beverage-vending-machine.glb
```

The source, export and thumbnail hashes in metadata identify the checked-in files; regenerated outputs should be remeasured if the Blender exporter or WebP encoder version changes. The uncompressed studio PNG is a local generated derivative, not a gallery asset.

# Shophouse Parcel Drop Hatch

One original fictional Singapore/Malaysia neighbourhood logistics fixture: a
short limewashed shopfront segment and cool green ceramic skirting frame a
real recessed enamel hatch. The bilingual purpose sign and ordinary geometry
are not a replica of a real shop or a carrier, and the cardboard parcel is
marked SAMPLE only. No carrier data, addresses, codes, safety assurances,
actual deposit, communications, locks or security behavior are included.

The native editable `.blend` starts closed. The exported glTF clip
`PARCEL_HATCH_OPEN` only turns the flap around its native lower hinge; the
parcel, label, support and surrounding masonry stay still. It opens to +70°
over local +X, holds, and is 1.8 seconds. The studio thumbnail shows the end
pose. For GLB the Y axis is up, Z outward, and coordinates are in metres.

```sh
blender -b --factory-startup --python-exit-code 7 -P generate.py -- --output /path/to/verification
blender -b --factory-startup --python-exit-code 7 -P verify_blender.py -- \
  shophouse-parcel-drop-hatch.blend exports/shophouse-parcel-drop-hatch.glb
node verify.mjs
```

The original 5.3.0 studio source keeps independent semantic parts and local
lighting, while the export joins material batches per parent, omits the
camera and external lights, and has exactly one animated quaternion track.
The generator's optional `--review` destination also renders closed and
close-up samples outside the catalog. Neither source nor runtime depends on
external textures, fonts (text uses the bundled Blender font converted to
meshes), data, assets or network services. The code and geometry are original
project assets; public download redistribution terms are not specified.

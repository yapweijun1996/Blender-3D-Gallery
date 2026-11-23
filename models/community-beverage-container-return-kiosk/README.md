# Community Beverage Container Return Kiosk

An original, fictional Singapore neighbourhood cabinet for a small illustrative
same-page 3D interaction. A labelled SAMPLE cylinder travels inward on a
visible horizontal guide; only after it parks does a two-sided amber/green
physical status flag show a tick. No real scanning, eligibility, queue, deposit,
refund, payment, accounts, network, waste handling, brand or venue is present.
The [NEA consumer page](https://www.nea.gov.sg/our-services/waste-management/beverage-container-return-scheme/for-consumers)
provides local thematic context only, not authorization, design or service claims.

The editable Blender 5.3.0 scene has individual parts, neutral studio lights
and two named movable parents. The glTF 2.0 export uses metre units, +Y up and
+Z toward the viewer. The single native `BCR_SAMPLE_ACCEPT` clip samples two
tracks: `BCR_SAMPLE_CAN.position` translates 0.425 m into the illustrative
opening over the first 1.3 s; `BCR_ACCEPT_FLAG.quaternion` rotates +180° about
its own Y axis between 1.3 and 1.7 s. Both hold through the 2.0 s end.

```sh
blender -b --factory-startup --python-exit-code 7 -P generate.py -- --output /path/to/isolated-output
blender -b --factory-startup --python-exit-code 7 -P verify_blender.py -- \
  community-beverage-container-return-kiosk.blend exports/community-beverage-container-return-kiosk.glb
node verify.mjs
```

The generator's `--review` writes additional studio evidence if requested,
outside the published Gallery scope. All geometry, neutral visual signage and
animation are original. The Blender bundled font is converted to geometry; no
external textures, services or dependencies are part of this model. Project
asset; redistribution terms for public downloads are not specified.

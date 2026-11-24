# Mall Fold-Down Changing Station

An original, unbranded Singapore mall-inspired family-room fixture. An empty warm-ivory tray swings on one captured transverse shaft inside an intentionally cropped tiled wall and dark teal shell. The visual fold-out only illustrates the authored shape and hinge. It depicts no infant, caregiver, load, straps, real installation, product, compliance or equipment-use guidance.

The [BCA City Square Mall family-room example](https://www1.bca.gov.sg/growth-and-transformation/bca-awards/ud-mark-award-winners/award-winners-2018/) and [BCA's historical 2019 code, Figure A7](https://www1.bca.gov.sg/docs/default-source/docs-corp-news-and-publications/publications/codes-acts-and-regulations/accessibilitycode2019.pdf?sfvrsn=ea84e8b7_0) document changing facilities and the fold-up type; neither source supplies this model's artwork, engineering specification, markings or depiction of an actual place.

## Native source

The editable Blender 5.3.0 source separates the tiled scene, fixed mounting shell, and moving deck. Blender is +Z up, -Y front; glTF is +Y up, +Z front. Studio lights and ground are excluded from GLB. The open still was rendered from the exact Blender geometry. The model viewer initially depicts the folded pose.

```sh
blender -b --factory-startup -P generate.py -- --output /tmp/changing-fixture --review /tmp/changing-fixture-views
blender -b --factory-startup --python-exit-code 9 -P verify_blender.py -- \
  mall-fold-down-changing-station.blend exports/mall-fold-down-changing-station.glb
node verify.mjs
```

One authored 2.20 s clip, `CHANGING_STATION_UNFOLD`, rotates `CHANGING_DECK_HINGE.quaternion` around the fixed X axis, from vertical to level with a held end pose. No other object moves. Independent Blender-native and Blender-GLB-import checks sample 133 poses each. The browser's gallery Reset restores the saved folded pose; the desktop/mobile display is a local visual demonstration, not a physical safety or performance test.

Original project asset; redistribution terms for public downloads are not specified.

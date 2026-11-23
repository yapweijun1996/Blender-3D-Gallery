# Malaysian Rail Service & Reload Counter

Original illustrative rail-station counter with a glazed staffed side, a projecting traveler shelf, a low handover tray and a molded receipt slot. A blank staff terminal is visible through the window. The physically modeled Malay and English signs distinguish Khidmat Pelanggan / Customer Service and Tambah Nilai / Reload.

- `malaysia-rail-reload-counter.blend`: editable parts, station groups, animation tracks and studio arrangement. Front is Blender −Y.
- `exports/malaysia-rail-reload-counter.glb`: self-contained +Y-up model with one nonlooping `RAIL_CARD_TAP` clip (0–2 seconds), whose only moving groups are `RAIL_DEMO_CARD` and `RAIL_READER_INDICATOR`. A labeled, unbranded demo card glides toward the pad and a green physical indicator becomes visible. Reset is the ready pose.
- `previews/studio.webp`: genuine 512 px Blender render of the ready pose. The asset contains no NFC, payment, amount, fare, data, storage, card identifiers, actual retailer signs or audio.
- Cultural/context source only: [Prasarana's Teroka Rapid background](https://singgahsebentar.myrapid.com.my/teroka-rapid.php?lang=en) mentions reload at customer service counters. The original model is not an operator design, location, authority, fare or compliance statement. No design, logo, texture, or content was copied. Public redistribution terms are not specified, so the Gallery download control is disabled.

## Reproduce and verify

From repository root with Blender 5.3, WebP tools and locked Node dependencies:

```sh
blender -b --python-exit-code 1 --python models/malaysia-rail-reload-counter/generate.py
cwebp -quiet -resize 512 512 -q 84 models/malaysia-rail-reload-counter/previews/studio.png -o models/malaysia-rail-reload-counter/previews/studio.webp
node models/malaysia-rail-reload-counter/verify.mjs
blender -b models/malaysia-rail-reload-counter/malaysia-rail-reload-counter.blend --python-exit-code 1 --python models/malaysia-rail-reload-counter/verify_blender.py -- models/malaysia-rail-reload-counter/exports/malaysia-rail-reload-counter.glb
```

Optional argument `-- --tap-review` renders close-up ready and acknowledgement evidence. Uncompressed renders and Blender backups are local derivatives only.

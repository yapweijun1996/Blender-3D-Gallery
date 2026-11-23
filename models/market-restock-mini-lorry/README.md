# Market Restock Mini-Lorry

Original stylized SG/MY neighbourhood restocking vehicle: a short-wheelbase
cab-over, low open dropside bed, vented reuse crates and anchored load straps.
Editable cab, panes, seat/interior, frame, wheel and cargo assemblies are kept
separate in the Blender file. The GLB reuses two crate meshes and shared tyre
and hub geometry without flattening their placement. No third-party textures,
brands, number plates or real vehicle geometry. This is a static illustrative
prop, not a drivable simulation or a claim about road use, vehicle or cargo
restraint compliance.

Metres, floor origin; Blender +Z up / −Y front, glTF +Y up / +Z front.

From the repository root with Blender 5.3 and WebP CLI:

```sh
D=models/market-restock-mini-lorry
blender -b -t 4 --python-exit-code 1 --python "$D/generate.py"
cwebp -quiet -resize 512 0 -q 86 "$D/previews/studio.png" -o "$D/previews/studio.webp"
blender -b -t 2 --python-exit-code 1 --python "$D/verify_blender.py"
node "$D/verify.mjs"
```

The studio is not exported. The verifier measures all wheel contacts and the
open cargo deck after Blender reimport, plus exact hashes and Khronos validation.
Blender scene serialization can vary across runs; verify the published candidate,
or refresh the measured source hash intentionally for a new export.

# Shophouse Jewellery Repair Bench

Original SG/MY neighbourhood repair-service prop with a walnut crescent work
surface, replaceable V-notched bench pin, visibly hollow filing collector, two
small tapered mandrels, sample ring blanks, and a jointed task lamp. The lamp
arms and hinges are separate editable meshes; the GLB is static and unlit.
English/Malay placards are generic. The model does not depict a real shop,
metal fineness or value, or provide repair, dust-handling or electrical guidance.

Metres, floor origin; Blender +Z up/−Y front, glTF +Y up/+Z front.
Run from the repository root with Blender 5.3 and the WebP CLI:

```sh
D=models/shophouse-jewellery-repair-bench
blender -b -t 4 --python-exit-code 1 --python "$D/generate.py"
cwebp -quiet -resize 512 0 -q 86 "$D/previews/studio.png" -o "$D/previews/studio.webp"
blender -b -t 2 --python-exit-code 1 --python "$D/verify_blender.py"
node "$D/verify.mjs"
```

The Blender test reimports the export and raycasts the V-notch, its prongs and
the exposed lower tray. The Node verifier validates the GLB and precise file
digests. No studio objects export. All modeling and images are original;
the lettering uses Blender bundled Bfont. Recompute hashes only for a
deliberately rebuilt and validated candidate.

# Monsoon Underpass Depth Marker

Original SG/MY monsoon-road-inspired prop: a mounted Malay/English water-depth
ruler, a short asphalt and concrete underpass cut, and a specifically recessed
grate with real open slots. The reflector-like marker and slate wear patches
are hand-authored materials and geometry, not a photometric performance claim.
The roadway scene shows no flowing or measured water.

Metres, floor origin; Blender +Z up/−Y front, glTF +Y up/+Z front. The illustration’s
20, 40, 60, 80 and 100 cm tick centers follow a shared roadway datum. These
are measurements on the model, **not** safe-depth thresholds, driving guidance,
a real installation, or a safety/accessibility/engineering certification.

Blender 5.3 and WebP CLI, from the repository root:

```sh
D=models/monsoon-underpass-depth-marker
blender -b -t 4 --python-exit-code 1 --python "$D/generate.py"
cwebp -quiet -resize 512 0 -q 86 "$D/previews/studio.png" -o "$D/previews/studio.webp"
blender -b -t 2 --python-exit-code 1 --python "$D/verify_blender.py"
node "$D/verify.mjs"
```

Blender reimport tests raycast the separate grate bars and dry recess below the
open slots. Studio lights and floor do not export. All geometry, materials
and pictures are original; bilingual lettering uses bundled Blender Bfont.
Recompute metadata digests only when intentionally making a new candidate.

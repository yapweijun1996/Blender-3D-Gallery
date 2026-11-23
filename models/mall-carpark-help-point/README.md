# Mall Car Park Help Point

Original modular SG/MY-inspired mall car park assistance pedestal set on a small
curb island. Weather hood, bilingual labels, grille, mounting and service panels
are editable. The button genuinely moves inward and releases in the authored
1.50 s sample, and an indicator switches from amber-ready to green-acknowledged
until reset. This is an on-device demonstration only: no call, audio, dispatch,
emergency service, operator affiliation, payment, data or vehicle/barrier control.
The proportions and labels are illustrative, not a compliance claim.

Coordinates: metres, Blender +Z up/−Y front, glTF +Y up/+Z front. The only clip is
`CARPARK_HELP_PRESS` with `CARPARK_HELP_BUTTON` (12 mm inward) and
`CARPARK_HELP_INDICATOR` (26 mm outward from a concealed position). The two
button labels follow its mesh; no studio/environment assets are exported.

From the repository root using Blender 5.3 and the WebP CLI:

```sh
D=models/mall-carpark-help-point
blender -b -t 4 --python-exit-code 1 --python "$D/generate.py"
cwebp -quiet -resize 512 0 -q 86 "$D/previews/studio.png" -o "$D/previews/studio.webp"
blender -b -t 2 --python-exit-code 1 --python "$D/verify_blender.py"
node "$D/verify.mjs"
```

Blender source serialization can change on rerun. Intentionally refresh measured
file digests only for a newly verified candidate. All geometry, materials and
studio composition are original; the letters use Blender's bundled Bfont.

# Ferry Jetty Raised Map Pedestal

Original static SG/MY-inspired ferry entrance prop: two slope-mounted plates at
different heights, with an imaginary coastline overview above an abstract jetty
deck detail. Land and station figures are independent meshes, and both orange
paths have physical relief above their water field. The text clearly identifies
both panels as examples. The deck stays small and does not recreate a terminal.

The maps and shapes are fictional. They show no actual location, timetable,
route, distances, accessibility standard or navigational advice. The samples
contain no Braille and are not tested or certified for accessibility, installation
or safety. All artwork and materials are original; letters use Blender bundled
Bfont and do not depict a real operator.

Metres, floor origin; Blender +Z up/−Y front, glTF +Y up/+Z front.
From the repository root with Blender 5.3 and the WebP CLI:

```sh
D=models/ferry-jetty-raised-map-pedestal
blender -b -t 4 --python-exit-code 1 --python "$D/generate.py"
cwebp -quiet -resize 512 0 -q 86 "$D/previews/studio.png" -o "$D/previews/studio.webp"
blender -b -t 2 --python-exit-code 1 --python "$D/verify_blender.py"
node "$D/verify.mjs"
```

The Blender verifier checks exported surface relief at both heights directly;
the Node verifier checks Khronos and file digests. No studio geometry exports.
Update measured digests only for an intentionally rebuilt and validated candidate.

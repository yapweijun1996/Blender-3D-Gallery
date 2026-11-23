# Wet-Market Coconut Scraper

Original SG/MY-inspired hand-cranked coconut scraper with an editable workboard,
clamped casting, clear conceptual guard, two offset gears on parallel shafts,
two coconut halves and an empty bowl. The general utensil type is documented by
the [Department of Museums Malaysia coconut grater exhibition](https://www.jmm.gov.my/en/coconut-grater-exhibition)
(background only, not a replica design or a claim of historic provenance).

The 2.0-second local demonstration `KELAPA_CRANK_TURN` turns a large amber
hand crank by 270°; the captive marked rotor turns 540° in the opposite direction.
The board, guard, preparations and bowl stay still. No cutting, output, sound,
power, actual equipment instructions, trade calibration or safety certification.
The visor and rounded rotor are visual geometry, not verified protective hardware.

Metres, floor origin; Blender +Z up/−Y front, glTF +Y up/+Z front. Both
native motion axes are local +X before signed rotation. To rebuild from the
repository root, use Blender 5.3 and the WebP CLI:

```sh
D=models/wet-market-coconut-scraper
blender -b -t 4 --python-exit-code 1 --python "$D/generate.py"
cwebp -quiet -resize 512 0 -q 86 "$D/previews/studio.png" -o "$D/previews/studio.webp"
blender -b -t 2 --python-exit-code 1 --python "$D/verify_blender.py"
node "$D/verify.mjs"
```

All geometry, materials and lettering composition are original (Bundled Blender
Bfont). No studio geometry exports. Only refresh recorded digests when intentionally
creating and revalidating a new candidate.

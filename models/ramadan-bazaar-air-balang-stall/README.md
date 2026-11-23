# Ramadan Bazaar Air Balang Stall

An original Malaysian-inspired outdoor Ramadan-bazaar drinks stall: taut
mulberry-and-oat awning, folding service table, three clear round balang
vessels with coloured drinks and ice, low spigots, cup trays and stacked
cups. Malay/English names are illustrative, not a standardized recipe or
claim about any particular seller. No real brand identity, pricing, ordering,
payment, hygiene, operational certification or external models/textures.

The one local sample `AIR_BALANG_POUR` runs for 2.25 seconds at 24 fps.
The featured tap physically tilts, a color-matched stream reaches the
aligned cup, its level rises, and the stream disappears. The cup stays
visibly filled until reset. This is an authored animation, not fluid physics
or dispensing instructions. The other taps do not move.

Context only: [Kampong Bharu Development Corporation’s account of the local Ramadan bazaar](https://www.pkb.gov.my/?p=6971)
and [Bernama’s reporting from a Kuala Lumpur Ramadan bazaar](https://www.bernama.com/bm/am/news.php?id=2525582).
No stall design, name, artwork or photograph was reproduced.

Metres; floor origin; Blender +Z up/−Y front, glTF +Y up/+Z front.
Use Blender 5.3 and the WebP CLI from the repository root:

```sh
D=models/ramadan-bazaar-air-balang-stall
blender -b -t 4 --python-exit-code 1 --python "$D/generate.py"
cwebp -quiet -resize 512 0 -q 86 "$D/previews/studio.png" -o "$D/previews/studio.webp"
blender -b -t 2 --python-exit-code 1 --python "$D/verify_blender.py"
node "$D/verify.mjs"
```

The studio is not exported. The Blender verifier checks the visible phase
geometry and the Node verifier checks raw glTF tracks, digests and Khronos
results. Recompute metadata digests only for an intentionally changed candidate.

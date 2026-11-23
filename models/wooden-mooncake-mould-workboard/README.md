# Wooden Mooncake Mould Workboard

An original static tabletop prop inspired by hand-carved wooden mooncake moulds
in the Singapore/Malaysia Mid-Autumn context. One connected hardwood handle and
bowl has a physical fluted negative recess. A separate cake shows the matching
raised mirror impression rather than a decal or repeated flat decoration. The
board has quiet grain and a folded striped cloth cushions a bamboo brush.

The object is not a copy of an exhibit, vendor product or cultural standard.
The crescent, two asymmetric seeds and eight-lobed blossom were authored for
this project. Sources establish the regional craft context, not this design:
[National Heritage Board: Katong–Joo Chiat heritage galleries](https://www.roots.gov.sg/stories-landing/stories/street-corner-heritage-galleries-katong-joo-chiat);
[National Heritage Board: Festivals in Singapore](https://www.roots.gov.sg/stories-landing/stories/festivals-in-singapore).
No external images, geometry, trademarks, recipes, food-contact approval or
production-use instructions are included.

Authored with Python and Blender 5.3.0. Fixed grain/brush seed: 836. The editable
`.blend` has separate semantic model groups and a studio collection not included
in the standalone GLB. Blender units are metres (+Z up), converted to glTF +Y up.

```sh
blender -b -P generate.py -- --output /path/to/own-staging
blender -b --python-exit-code 7 -P verify_blender.py -- \
  wooden-mooncake-mould-workboard.blend exports/wooden-mooncake-mould-workboard.glb
node verify.mjs
```

`generate.py` also accepts `--detail /path/to/detail.webp` for a closer QA view;
this is not a second model or published dependency. `verify_blender.py` checks
the closed source solids, local-X mirror relationship across 3,520 samples,
cavity depth, positive relief and re-imports the exported GLB for paired
raycasts against real geometry. Light, material and preview rendering can vary
with Blender version; recorded hashes pin the authored deliverables.

Original project asset; redistribution terms for public downloads are not
specified. Gallery viewing only.

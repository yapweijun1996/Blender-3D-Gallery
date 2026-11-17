# Elevator Interior

Original low-priority GJH Virtual Mall car interior. Four telescoping sliding
door leaves are modelled open; rear mirror, supported handrails, eight unlabelled
buttons, ceiling light and neutral wall panels. No text, brands or external assets.

Metres; finished-floor-centre origin. Blender +Z up / -Y front exports to glTF +Y
up / +Z front. The walking surface, sill and recessed track tops meet Y=0.
The base extends to Y=-0.06 m; reserve that recess beneath the mall floor. The
roof reaches Y=2.34 m, retaining the 1.60 x 1.50 x 2.40 m total envelope.
Envelope and clearances are measured in `reports/assets.json` and
`reports/sources.json`. Three shared materials and ten delivery meshes; editable
source parts are batched only in a temporary export copy. Matte colours use
vertex attributes; no textures or decoder dependencies.

Measured delivery: 9,836 triangles, 11,038 vertices, 393,568 bytes (384.3 KiB),
3 materials and 10 mesh primitives. Door aperture: 0.90 x 2.14 m. Advisor round
1 softens metal highlights, reduces diffuser emission and uses asset-local
lighting with a near-front view. The control panel sits 0.12 m farther back to
keep both button columns visible alongside the rear mirror. The existing gallery
supports direction and lighting overrides; its automatic fit has no asset-local
zoom setting. `reports/acceptance.json` identifies the current verification;
older iteration logs are retained as historical evidence.

```sh
/opt/homebrew/bin/blender --background --python-exit-code 1 --python models/elevator-interior/generate.py
sips -s format jpeg -s formatOptions 88 models/elevator-interior/previews/hero.png --out models/elevator-interior/previews/hero.jpg
node models/elevator-interior/validate.mjs
/opt/homebrew/bin/blender --background --python-exit-code 1 --python models/elevator-interior/inspect_sources.py
npm run validate:assets
npm test
npm run build
node models/elevator-interior/browser-check.mjs
node models/elevator-interior/verify_presentation.mjs
```

Add `-- --export-source` to the generator to preserve saved source edits;
`-- --skip-render` suppresses previews. Source generation has no random inputs.
`inspect_sources.py -- --edit-copy` tests a temporary mirror edit without saving
over the source. The asset-local validator also accepts another GLB path.
Run `python3 models/elevator-interior/verify_rebuild.py` after source inspection
to compare a generator-only rebuild and saved-source re-export byte for byte.
The presentation check uses the measured browser canvas, delivered geometry and
source button centres to test default-view sightlines. `floor-fit.png` shows
the sill against a studio-only adjacent mall floor at Y=0; that floor is excluded
from the saved asset and GLB.

`hdb-lift-interior` and `passenger-lift` are similar, but lack the requested rear
mirror and/or this compact open-door configuration. Exact match NOT FOUND;
see `reports/duplicate-search.json`. This asset has its own collection in the
existing Mall Fixtures category.

Static geometry only: buttons, doors and transport have no runtime behaviour.
The mirror is an environment-reflective metallic PBR panel, not a live planar
reflection. The ceiling is emissive but exports no light object. Full mall
integration, aggregate 200 draw-call budget, physical devices and WebKit are
unverified. Original asset for owner-project reuse; public redistribution terms
unspecified. Local draft, no push or publication.

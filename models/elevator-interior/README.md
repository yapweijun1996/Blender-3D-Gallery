# Elevator Interior

Original low-priority GJH Virtual Mall car interior. Four telescoping sliding
door leaves are modelled open; rear mirror, supported handrails, eight unlabelled
buttons, ceiling light and neutral wall panels. No text, brands or external assets.

Metres; floor-centre origin. Blender +Z up / -Y front exports to glTF +Y up / +Z
front. Envelope and clearances are measured in `reports/assets.json` and
`reports/sources.json`. Three shared materials and ten delivery meshes; editable
source parts are batched only in a temporary export copy. Matte colours use
vertex attributes; no textures or decoder dependencies.

```sh
/opt/homebrew/bin/blender --background --python-exit-code 1 --python models/elevator-interior/generate.py
sips -s format jpeg -s formatOptions 88 models/elevator-interior/previews/hero.png --out models/elevator-interior/previews/hero.jpg
node models/elevator-interior/validate.mjs
/opt/homebrew/bin/blender --background --python-exit-code 1 --python models/elevator-interior/inspect_sources.py
npm run validate:assets
npm test
npm run build
node models/elevator-interior/browser-check.mjs
```

Add `-- --export-source` to the generator to preserve saved source edits;
`-- --skip-render` suppresses previews. Source generation has no random inputs.
`inspect_sources.py -- --edit-copy` tests a temporary mirror edit without saving
over the source. The asset-local validator also accepts another GLB path.

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

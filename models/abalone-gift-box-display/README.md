# Abalone Gift Box Display

Original S10 P2 countertop display: three stepped tiers, twelve leaning lacquer-look
gift boxes in red, champagne gold and black, twenty-four plain cans, clear lids,
ribbon bands, twelve blank cards and a blank sign. Small cradles support each box.
No logos, text, external models, packaging artwork, textures or downloaded assets.

Advisor round 1: replaced the two intersecting sign posts with one central post
in the 20 mm gap between boxes. Evaluated source geometry measures 4.000 mm of
clearance to each adjacent box, a flush rear-riser seat and 5.000 mm of engagement
with the sign frame. `inspect_sources.py` checks separation from all twelve boxes
and both connections; the clearance check rejects the original source layout.

Measured delivery: 18,948 triangles, 22,056 vertices, 728,648 bytes, three shared
materials and three mesh primitives/draw calls; no textures or degenerate
triangles. GLB dimensions (X/Y/Z): 1.000000 / 0.900000 / 0.500000 m.

Metres; floor-centre placement datum (place on the shop counter), Blender +Z up
and -Y front, exported glTF +Y up and +Z front. Static visual prop, with no
opening animation, colliders or purchase logic. The editable source keeps all
gift components separate. Evaluated export copies merge into three shared
material primitives; lacquer colors use vertex colors. The clear lid uses thin
single-sided alpha blending, an economical approximation without refraction.

```sh
/opt/homebrew/bin/blender --background --python-exit-code 1 --python models/abalone-gift-box-display/generate.py
/opt/homebrew/bin/blender --background --python-exit-code 1 --python models/abalone-gift-box-display/inspect_sources.py
node models/abalone-gift-box-display/convert-preview.mjs
node models/abalone-gift-box-display/validate.mjs
node models/abalone-gift-box-display/verify_source_edit.mjs
npm run validate:assets
npm test
npm run build
node models/abalone-gift-box-display/check-browser.mjs
```

`-- --export-source --skip-render` exports saved source edits; `-- --skip-render`
rebuilds without rendering. Five PNG previews (hero, front, side, 3q and rear)
are rendered from the actual reimported GLB. `reports/assets.json` records measured
bounds, topology, resources and hash;
`reports/source.json` records independently reopened source features, and
`reports/khronos.json` contains the full format validator output. Browser evidence
is scoped to the local production build in headless Chromium, including the GLB
response hash, actual WebGL draws, rotation, zoom and reset. Physical devices,
WebKit, assembled-mall performance and deployment remain unverified.

Exact match was NOT FOUND across catalog IDs/names/tags and metadata. Related
assets are the existing GJH abalone cans, `stacked-can-pyramid`,
`mooncake-gift-box` and `christmas-gift-boxes`; none provides the requested clear-lid
two-can gift display. They remain unchanged. Search evidence is retained in
`reports/duplicate-search.json`. Rights are described in `LICENSE.md`.

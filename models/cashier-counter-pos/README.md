# Cashier Counter with POS

Original brand-neutral cashier station for the GJH Virtual Mall. A 1.4 x 0.7 m
counter has its work surface at 0.95 m, a staff-facing blank touchscreen,
customer-facing card reader with unmarked keys, receipt printer with blank paper,
under-counter cash drawer, compact two-hook bag stand and blank countertop sign.
Open staff shelves and a cupboard complete the back. Three shared materials;
three batched GLB meshes. No external assets, textures, text, logos or packaging.

Metres; floor-centred root `ASSET_CashierCounterPOS`. Blender +Z up / -Y front
exports to glTF +Y up / +Z front. The main screen faces the staff aisle (-Z in
glTF). Hero view shows the staff side; front and 3q previews show the customer side.
The source retains individual editable components. The export batches evaluated
copies by material without modifying the source. Static visual prop; no actual
payment, printer, drawer animation or shop software is provided.

Advisor round 1: the card-reader support now terminates 4 mm inside the tilted
housing's back. The receipt's rear edge is anchored inside the paper slot, with
its free end feeding downward through the front opening. The source audit checks
the evaluated attachment surfaces and matches all joint vertices to the imported
GLB within 1 micrometre. The generator also refreshes the gallery's hero JPEG.

Measured export: 9,964 triangles, 399,428 bytes (0.381 MiB), three meshes,
primitives and materials; bounds 1.400 x 1.421 x 0.700 m (glTF X/Y/Z).
Khronos validation: zero errors and warnings. See `reports/` for measured evidence.

## Rebuild and checks

Run from the repository root:

```sh
/opt/homebrew/bin/blender --background --python-exit-code 1 --python models/cashier-counter-pos/generate.py
node models/cashier-counter-pos/validate.mjs
/opt/homebrew/bin/blender --background --python-exit-code 1 --python models/cashier-counter-pos/inspect_sources.py
npm run validate:assets
npm test
npm run build
node models/cashier-counter-pos/verify_browser.mjs
git checkout -- models/demo-beverage-can/reports/structure-motion.json
```

Use `--export-source` after Blender's `--` to export the saved editable source
without rebuilding, optionally adding `--skip-render`. The source audit edits a
temporary copy, reopens/re-exports it, then imports and renders the canonical GLB.
The browser check verifies the consumed GLB hash, real draw calls, orbit, zoom,
reset, refresh and reopening at 1440 x 900. Evidence is in `reports/`.
Physical devices, WebKit, integrated mall placement and overall mall performance
are not verified. Local draft only; publication belongs to the manager.

## Existing models checked

`checkout-counter` is a conveyor checkout with scanner and bagging platform;
`self-checkout-machine` is a self-service kiosk. `cash-register` and `pos-terminal`
are standalone devices. None includes this counter's complete requested features.
See `reports/reuse.json` for the catalog and metadata search. This distinct asset
follows the owner's exact-match override; no existing models were changed.

# Mall Event Booth

Original jade, champagne-brass and walnut mall event-booth kit for a replaceable campaign poster and display vignette. `PosterPanel` and `DisplayContent` are independent source collections and independent mesh-bearing GLB groups; hiding or replacing one does not remove the other. The gallery viewer consumes the exported GLB and does not edit it live.

## Editing

Open `sources/mall-event-booth.blend` in Blender. Edit the poster face and the editable headline/subhead under `PosterPanel`; edit or replace merchandise, cards, tray, or label under `DisplayContent`. Preserve those collection names if downstream replacement is required. The delivered `.blend` is the editable source of record; manual source edits should be kept when producing a new export, and are not discarded by this documentation.

## Construction and parameters

The booth is procedural geometry in metres: a 2.72 m wide charcoal floor plinth, walnut counter, jade wings, brass accents, framed ivory campaign panel, and a small raised display. The source camera approaches from positive Y, where the poster art faces, so the headline remains legible in the preview. Dimensions and measured export metrics are recorded in `metadata/mall-event-booth.json` and `reports/assets.json`.

## Provenance and licensing

All geometry, materials, labels, and artwork are original to this project. No external or branded imagery, textures, or models are used. Labels use Blender's bundled Bfont and remain editable source text before export. Reuse in the owner's projects is authorized; public redistribution terms have not been specified. This is a concept asset, not an official mall product, fabrication, accessibility, or engineering specification.

## Verification

From `repo/`:

    ../blender-local.sh --background --python models/mall-event-booth/generate.py
    ../blender-local.sh --background --python models/mall-event-booth/inspect_sources.py
    python3 models/mall-event-booth/prepare_previews.py
    node models/mall-event-booth/validate.mjs

The focused contract is `tests/mall-event-booth.test.mjs`. It checks the measured SHA, mesh-bearing independent groups, and isolation of replacement/hide operations.

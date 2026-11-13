# Item 431 verification

## Result and integration boundary

**Local asset PASS. Initial old-base application gates PASS. Final merged-base integration PENDING / NEEDS REVIEW.**

This workspace was cloned locally from the clean item 430 preparation at `52184ee9c4de798830fbe560febf1947e4a5f14a`, descended from main `b7421d284b503ff923508fc3046b2193108f503a`. A read-only remote main check immediately before the initial gates still returned that main SHA. No PR 12 implementation was copied. The retained item 430 old-loader failure evidence is unchanged; item 431's first strict run did **not** reproduce ERR_ABORTED. That one successful run does not establish the old loader is fixed, nor replace the required full gates after PR 12 reaches main and accumulated assets are integrated.

No remote push, PR, merge, deployment, shared-history rewrite, application/UI change, schema change, or new viewer display field was made. Existing `previewRotationY` is the only viewer parameter used. The catalog append preserves all existing collection objects and rights/download settings. The original item 430 workspace remained clean and untouched.

## Executed local checks

- Generator and five source renders completed under Blender 4.0.2, two CPU threads, Python exit-code enforcement. Python syntax check PASS.
- GLB **99,924 bytes, 2,608 triangles, 3,308 vertices, 16 mesh primitives, six materials**, zero textures and animation clips. SHA-256: `b78f11cc2da1c3bffc4ca226a46a95b345120b7f955e3a71e7a4e632f52f2f7b`.
- Khronos glTF Validator: **0 errors / 0 warnings**. Self-contained buffers; no studio cameras/lights, external files or decoder requirement.
- Measured metre-scale bounds: 0.14 × 0.34 × 0.0344 m. Real faceplate apertures verified by raycasting; 3 mm faceplate and 1.5 mm housing back; wall anchor verified. Each 24 mm-radius button fits a 25 mm aperture with 1 mm radial clearance. Independent 2 mm inward poses clear the housing and leave the cap face forward of the faceplate; arrow geometry follows its own cap.
- Shipped `.blend` source reopened. Both button pivots posed independently. A separate temporary copy received a real +2% X-width edit to the Up cap and a 2 mm Up pivot press; that source was saved, reopened and re-exported. GLB coordinate comparison confirms **15 other meshes unchanged**. Edited GLB also validated 0/0. Shipped source hash unchanged. This is source editability, not runtime button behavior.
- Focused unit tests **5/5 PASS**. Full unit suite **124/124 PASS**. `npm run build` **PASS**, including catalog-wide asset validation. No lint/typecheck scripts are defined by this checkout.
- Library regression suite **9/9 PASS**, including static indexes, search/filter URLs, direct-link refresh/history, error retry, no-WebGL fallback, mobile menu, demo lifecycle and reflow/reduced-motion coverage.

## Strict browser evidence, one initial-base run

Desktop Chromium **156.0.8078.4**, software WebGL, viewport emulation only:

| Viewport | Strict result | Actual GLB SHA/bytes | HTTP | Request/console/page errors | Controls and lifecycle | Overflow |
| --- | --- | --- | --- | --- | --- | --- |
| 1440 × 900 | PASS | exact match | all 200 | none | orbit, zoom, exact reset/reopen, 3 repeated close/open cycles | none |
| 768 × 1024 | PASS | exact match | all 200 | none | orbit, zoom, exact reset/reopen, 3 repeated close/open cycles | none |
| 390 × 844 | PASS | exact match | all 200 | none | orbit, zoom, exact reset/reopen, 3 repeated close/open cycles | none |

Draw calls were observed in every case, rendering stopped on close, focus returned to the asset card, download was hidden, and complete unmasked canvas hashes matched after reset and reopening. No requestfailed/ERR_ABORTED suppression or retry-to-green was used. See `reports/initial-base/browser/results.json` and the corresponding screenshots. The test exercised gallery view controls, **not** physical button clicks or elevator operation.

**Android hardware: NOT TESTED. iOS hardware: NOT TESTED.** Emulated mobile viewport results are not device certification.

## Visual inspection

Viewed actual pixels in `previews/contact-sheet.webp` and `reports/initial-base/browser/contact-sheet.webp`. All five Blender views are recognizably a simple metal lift call panel, with distinct up/down arrows, round caps/bezels, separated faceplate and thin charcoal housing. Rear view shows the plain closed housing back. The existing browser lighting makes the satin metal darker than the studio render, but both arrows and the complete panel remain legible and unclipped across all three sizes. No additional lighting or UI changes were introduced to improve the screenshot. All five gallery WebPs are below 18 KiB.

No runtime elevator call, electrical integration, tactile/braille/code compliance, fabrication readiness or installation certification is claimed. Optional-looking amber indicator glow is static material emission only.

## Evidence

- `reports/assets.json`, `geometry.json`, `sources.json`, `source-edit.json`.
- `reports/generate.log`, `render-views.log`, `prepare-previews.log`, `validate.log`, `source-edit.log`, `source-edit-validation.log`, `focused-unit.log`.
- `reports/initial-base/{remote-main-before-gates.txt,exits.json,unit.log,build.log,browser.log,library.log}`.
- Full browser and library screenshot/result directories remain under `reports/initial-base/`. Build log trailing spaces were normalized for diff hygiene; no log lines or failures were filtered.
- `reports/preservation.json` records the append-only catalog check.

Final integration must rerun full unit/build, exact-byte strict three-viewport checks, and library regression against the actual merged base. Current local success must not be labeled release-ready or production-tested.

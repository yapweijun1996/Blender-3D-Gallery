# Floor direction sign verification

Date: 2026-11-12. Base: `fc2fff8`, the main commit that already contains merged event booth PR #9. Only the floor-sign asset pack, new focused tests and one catalog insertion were changed. All pre-existing catalog entries and application code remain unchanged.

## Asset and source

- Blender 4.0.2 generation and actual saved-source reopening: PASS.
- GLB: **561,892 bytes**, **13,404 triangles**, 19,800 vertices, 19 primitives, five materials, no animations or textures.
- SHA-256: `4c1f7edd051597ed4aae918d891051ed4da1d7cc5a2e5d70da84f55c8732fea6`.
- glTF XYZ bounds: 1.24 × 2.53 × 0.54 m, minimum Y = 0.
- Khronos glTF Validator 2.0.0-dev.3.10: **zero errors and zero warnings**.
- The 19 primitives deliberately preserve independent material slots across six replaceable mesh-bearing modules. This exceeds the preferred eight-primitive target, not the hard byte/triangle budgets.
- The PNG/WebP thumbnail was pixel-reviewed: legible destination labels, correct arrows and level badge, no visible interpenetration.
- A saved-source mutation in an isolated copy changed “Dining” to “Gourmet”, then ran the documented `--export-source` mode. Only `DirectionDining` geometry changed; mesh geometry, world transforms and materials of the other five groups remained hash-identical. Both exports passed Khronos validation. The shipped original GLB remained unchanged. See `reports/source-edit.json`.

## Executed checks

- `npm test`: **109/109 PASS**, including four new asset contract tests.
- `npm run build`: PASS, including complete asset validation. The existing Vite large-chunk warning remains.
- `node scripts/test-mall-floor-direction-sign.mjs`: PASS at **1440×900, 768×1024 and 390×844**.
- The focused script checks actual WebGL draw activity, cleared loading status, exact consumed GLB byte count and SHA-256, all GLB responses = 200, no request failures (including ERR_ABORTED), no console/page errors, orbit/zoom/reset screenshot changes, and no horizontal page overflow.
- `npm run test:library`: **all nine scenarios PASS**, including static asset preservation/lazy loading, combined filters, history/refresh, failed-load retry, WebGL fallback, keyboard menu behavior, demo lifecycle, reduced motion and reflow.
- Initial screenshots at all three widths were pixel-reviewed and show the FRONT, orange “02” badge, destination labels and correct arrows. Fine-print sublabels are naturally small in the fitted mobile view; zoom remains available.
- Existing rights policy is retained and asserted: the gallery download control is hidden.
- Final screenshot evidence and structured results are in `reports/screenshots/` and `reports/browser.json`.

## Attempt history

The first strict browser run stopped on the hidden-download assertion because the new catalog entry initially omitted `downloadable: false`. This was a real integration defect, corrected in the catalog; a unit assertion was added for both the disabled download flag and its rights string. No assertion or request-failure event was removed, filtered or weakened. The final production build and full unit suite were rerun before the passing browser run.

The Blender generator, source inspection and Khronos checks passed on their first runs. An unrelated catalog formatting change caused by JSON serialization was removed before final verification so existing catalog text stays exact.

## Scope

Labels and arrows are editable in Blender, not through the gallery UI. Browser verification is automated desktop Chromium with software WebGL, not physical-device touch or a GPU performance benchmark. No architecture/UI changes, deployment, merge, remote push or PR creation were performed during this implementation.

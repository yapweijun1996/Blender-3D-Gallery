# Waste sorting station verification

Date: 2026-11-12. Base: `f0017a7` (fresh main, includes merged floor-direction-sign PR #10). No UI, viewer architecture, prior assets or existing tests changed. Catalog adds one collection immediately before `mall-essentials`; the existing single `mall-trash-bin` remains intact.

## Exact delivered model

- GLB: **479,436 bytes**, SHA-256 `52a62e5ace403100b7757ac0c4b464272f5d46c79903c69d5d2db75a83a2e4ae`.
- 11,508 triangles; 16,835 exported vertices; 22 primitives; seven materials; no animations, textures or external buffers.
- Khronos glTF Validator 2.0.0-dev.3.10: **0 errors / 0 warnings**.
- Bounds: 1.90 m wide × 1.35 m high × 0.63 m deep in glTF XYZ. Floor at Y=0, centred X/Z.
- `StationFrame`, three `*Compartment` bodies and three `*Lid` groups are independent root children with real mesh geometry. Mesh data is also semantically named.

## Source and replacement verification

- Blender 4.0.2 reopened the saved `.blend`. Seven named collections and editable FONT labels inspected, metric units and ground origin checked (`reports/sources.json`).
- The isolated source-edit test loaded the saved source, changed the actual Recycle label from RECYCLE to PLASTIC, saved the copy, and ran the real `--export-source` path. This does not regenerate the canonical design.
- Both original and edited exports pass Khronos 0/0. Per-module world transforms, geometry attributes, indices and material values are hashed: **only `RecycleLid` differs; the other six groups are identical**. Original asset SHA remains unchanged (`reports/source-edit.json`).
- Five focused tests additionally verify catalog/metadata consistency, measured bounds, independent replacement and real apertures. Downward raycasts through each lid have no top hit and first strike the corresponding liner bottom at 0.1725 m, not a concealed solid top.

## Full checks and browser evidence

- `npm test`: **114 passed, 0 failed, 0 skipped**.
- `npm run build`: passed, including the full catalog asset validator. Existing Vite warning about a minified chunk over 500 KB remains; no chunk settings were changed.
- Focused browser: **1440×900, 768×1024, 390×844** all passed in the first full run and the final unchanged repeat against the actual production build. An intervening audit failed as disclosed below. Each viewport verifies the exact consumed GLB bytes/SHA, HTTP 200 responses, real WebGL drawing, keyboard orbit/zoom and reset changing screenshots, no horizontal overflow and hidden download control. `requestfailed`, console errors, page errors and HTTP errors are all strict failures; none were ignored or filtered.
- Existing library browser suite: **9/9 passed**, including static-index no-GLB behavior, search/filters, history/reload, failure retry, WebGL fallback, keyboard mobile-menu flow, demo cleanup and reduced-motion/reflow checks.
- Independently viewed the actual Blender preview and all three initial browser screenshots. The labelled front is visible initially; all three openings, color-coded lids, pictograms and complete base fit without clipping. Gallery and Blender lighting differ as expected. Small detail captions naturally become small at mobile scale.
- `reports/screenshots/` preserves the three initial browser images. The focused runner writes initial, orbit, zoom and reset screenshots for each viewport.

## Limits and honest scope

This is a static, editable decorative mall asset. Source-level replacement and export are proven; live recycling, runtime label editing, physical bin/door operation and lid animations are not implemented. There is no claim of local waste-rule compliance, structural/fabrication suitability or accessibility certification. No production deployment was performed.

### Intermittent strict browser failure retained

An intervening audit rerun passed desktop and tablet but failed the strict mobile `requestfailed` assertion with `net::ERR_ABORTED` on the exact GLB URL. The model had still rendered and its exact consumed SHA matched, but this does **not** excuse the failure. `reports/browser-audit-failure.log` and the partial `reports/browser-audit-failure.json` retain the evidence. An unchanged repeat passed all three viewports, with zero request/console/page errors and HTTP 200 recorded in `reports/browser.json`.

The viewer/application source is unchanged. The abort's root cause has not been established or fixed by this asset-only task; browser-request intermittency remains a limitation, not a clean reproducibility claim. No errors were suppressed and no test was weakened. Asset-generation, source-validation, unit and library-browser checks had no failures. The 22-primitives tradeoff is documented rather than hidden: independently editable modules retain their material slots, above the preferred eight-primitive target but below the explicit 26-primitive hard budget.

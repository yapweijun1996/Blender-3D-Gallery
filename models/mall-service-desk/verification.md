# Service desk verification

Local implementation on feat/mall-service-desk, based on main 4c9f57eddb25562a50ee1ab171b40e128b403767 (including the mascot addition). No remote push, PR, merge or deployment was performed. Final scoped checks passed; the earlier intermittent browser failures remain recorded below.

## Passed checks

- Real GLB passed Khronos glTF Validator 2.0.0-dev.3.10 with zero errors and warnings: 8,024 triangles, 245,748 bytes, five material primitives, no textures, external resources, cameras, lights or animations. Floor-centred metre-scale export. See reports/assets.json.
- Blender 4.0.2 source reopened with 37 editable authored parts, metric units, floor origin and editable SERVICE font text. See reports/sources.json.
- Studio thumbnail and actual desktop/mobile viewer pixels visually inspected. Counter, lower guest section and raised sign are visible and fit the frame.
- npm test: 92 passed, zero failed.
- npm run build: passed, including all 58 catalog GLBs. Existing large-chunk warning remains.
- npm run test:library: nine existing browser cases passed.
- Service desk matrix: all three discovery cases passed at 1440, 768 and 390px, with thumbnail decoding, search, hidden downloads, no eager GLB loads and no horizontal overflow.
- All three actual viewer flows rendered complete GLBs whose byte counts and SHA-256 matched the registered source, and passed keyboard orbit, zoom, reset, refresh, Escape, reopening, focus restoration and render-loop cleanup checks.

## Browser revalidation and retained diagnostic failures

After reconciling latest main, the final unchanged service-desk matrix passed all six cases and the existing library suite passed all nine cases. All three final initial-view screenshot hashes match the already visually reviewed images. This passing rerun does not resolve the prior intermittent network signature.

The initial run of node scripts/test-mall-service-desk.mjs exited 1: four of six cases passed, two failed. Desktop and tablet each reported a GLB net::ERR_ABORTED event despite complete consumed bytes and successful rendering/interaction checks. The mobile case fully passed. The no-network-errors assertion remains unchanged. No viewer/loader code or existing test was modified, and no exception was suppressed.

This matches the signature already seen in the four-asset pack and the existing loading diagnosis, but is not proof of an underlying Chromium/Three.js cause. See reports/browser-first-attempt.json and reports/browser-first-attempt.log for the failures, and reports/browser-results.json and reports/browser.log for the final passing run. The harness observes the original Response.arrayBuffer return and preserves response behavior.

The unrelated Game UX fine-left-aim failure reported on the baseline and first pack was not rerun or changed here. Physical touch, Safari, real mobile GPUs, screen readers, fabrication and accessibility compliance are unverified. The source sign is editable; the exported sign is static geometry.

## Local delivery

Separate asset folder, focused tests and one appended catalog collection; no architecture, Game, consumer mall, licensing or download-policy change. The pending first pack is neither modified nor required. Reconcile the append-only catalog addition when publishing after that pack. Review rights before any change to public redistribution policy.

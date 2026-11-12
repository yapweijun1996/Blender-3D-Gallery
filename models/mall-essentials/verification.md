# Mall Essentials verification

Status: four assets implemented and validated; local browser diagnostics have explicit failures. This is a reviewable gallery addition, **not** a fully green browser suite or deployment.

Baseline: main commit 8b21a337f522c12ce4eb1627b4ca7ee2aa0b8fa1. Isolated branch: feat/mall-essentials-four-models. Authoring: Blender 4.0.2 on Ubuntu ARM64, CPU Cycles. Browser: Chromium 156.0.8078.4 with SwiftShader; Node 22.23.3.

## Passed

- Four real glTF 2.0 exports passed Khronos glTF Validator 2.0.0-dev.3.10 with **zero errors and zero warnings**. Each has a floor-centred origin, metre-scale bounds, no external resources, at most six material primitives, and fits the 20,000-triangle / 700,000-byte per-asset budget.
- Four editable .blend sources were reopened in Blender: 23 kiosk, 18 lightbox, 32 bin and 31 shelf authored parts. Studio objects remain separate from the exported asset. See [source inspection](reports/sources.json).
- The four WebP thumbnails were decoded in the browser and their actual pixels reviewed. All four desktop and 390px model views were visually inspected for framing, identifiable geometry and front-label orientation. Representative screenshots are in [reports/screenshots](reports/screenshots).
- **95 unit tests passed**, including five new collection/provenance/hash/budget tests. Production build passed and validated all **60 catalog GLBs**. The existing large-chunk advisory remains; no bundling behavior was changed.
- Existing library browser suite: **9 cases passed**, including search/filter, details, history, failure/retry, unavailable WebGL and mobile menu.
- Final mall matrix: **all 3 discovery cases passed** at 1440, 768 and 390px, with four decoded thumbnails, no eager GLB requests, no canvas before opening a model, search and no horizontal overflow.
- All **12 actual model/viewport flows** completed rendering, keyboard orbit, zoom, reset, refresh, Escape, reopening, close/focus return and stopped-render-loop assertions. Actual viewer-consumed GLB buffers matched source SHA-256 and byte counts. These interaction checks do not erase the network failures below.

See [summary](reports/summary.json), [asset measurements](reports/assets.json), [final browser results](reports/browser-results.json), [unit log](reports/unit-tests.log), [build log](reports/build.log) and [library log](reports/library-browser.log).

## Browser diagnostic failures retained

The final 15-case mall suite exited **1**: **7 passed, 8 failed**. Eight viewer cases reported Chromium net::ERR_ABORTED for a GLB even though its complete consumed buffer matched the source and the model rendered and passed the interaction flow. The no-network-errors assertion is preserved. No production loader/viewer code was changed or exception suppressed.

This signature is consistent with the pre-existing Three.js streamed-response behavior documented in [the gallery's loading diagnosis](../../docs/game/loading-root-cause.md). It is not proof of the browser's underlying cause, nor a claim that every browser/device is unaffected.

Two initial runs using Playwright response.body() stopped on the bin because Chromium Network.getResponseBody could not retrieve the response. The first hypothesis was navigation timing; awaiting body capture before reload did **not** fix it. The corrected instrument observes the original Response.arrayBuffer result consumed by GLTFLoader, verifies magic/version/length/SHA-256 and returns the same buffer unchanged. It does not replace a response or alter model bytes. A third run then exposed the ERR_ABORTED assertion. The final collect-all run retained every assertion and a failing exit code while collecting all 15 cases.

Original records: [first](reports/browser-first-attempt.json), [second](reports/browser-second-attempt.json), [third](reports/browser-third-attempt.json); matching logs and the final log are retained in reports. No further harness retry or production workaround was applied.

## Existing Game UX diagnostic

The separately requested read-only existing Game UX run passed three earlier cases, then failed **scripts/test-game-ux.mjs:233**, “fine left adjusts aim by one degree.” This is the same assertion reported on the baseline's existing CI. This addition changes no Game code, tests, workflow or application UI. The failure was not repaired, weakened or retried. See [raw diagnostic](reports/game-ux-diagnostic.log).

## Reproducibility and limits

The initial local Blender export attempt lacked NumPy; the local authoring dependency was supplied and generation rerun. The failed authoring log remains in the task workspace. Final export validation and source reopening ran after that correction.

No main push, merge, production deployment, workflow run, third-party asset download or new public redistribution license occurred. The consumer mall was not changed. Physical mobile GPUs, Safari/touch gestures, screen readers, long-duration memory/thermal behavior and fabrication accuracy remain unverified. The emissive poster is a decorative material, not a calibrated light source.

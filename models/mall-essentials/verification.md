# Mall Essentials verification

Status: four assets implemented and validated; local browser diagnostics have explicit failures. This is a reviewable gallery addition, **not** a fully green browser suite or deployment.

Original baseline: main commit 8b21a337f522c12ce4eb1627b4ca7ee2aa0b8fa1. Current integrated base: **4c9f57eddb25562a50ee1ab171b40e128b403767**. Isolated branch: feat/mall-essentials-four-models. Authoring: Blender 4.0.2 on Ubuntu ARM64, CPU Cycles. Browser: Chromium 156.0.8078.4 with SwiftShader; Node 22.23.3.

## Latest-main reconciliation

The owner approved merging latest main into the feature branch to resolve PR #6's conflict. A normal merge preserves feature commit 51ef7b8f73b56fd228652828d9f038d3e1d11aff and main 4c9f57eddb25562a50ee1ab171b40e128b403767 without rewriting shared history. The only conflict was the catalog append. Every main collection, including the newly merged mascot, is preserved exactly; the four-model collection is appended unchanged. Existing GLB, Blender source and preview bytes are unchanged.

Fresh integrated-tree verification:
- **95 unit tests passed; production build and all 61 catalog GLBs passed.**
- Four essentials passed measured validation again with zero errors/warnings.
- **9 library browser cases and 3 mascot browser cases passed.**
- Mall matrix completed all **15 cases: 10 fully passed, 5 retained ERR_ABORTED failures**, exit code 1. All 3 discovery cases and all 12 viewer interaction/consumed-byte checks passed. This single integration run is not evidence that the pre-existing diagnostic improved.
- The previous Game UX failure remains documented below. No Game file changed on either merge side, and no extra Game retry or workaround was applied.
- No PR merge into main, deployment or force push was performed.

Current evidence: [summary](reports/summary.json), [integration matrix](reports/integration-browser-results.json), [unit log](reports/integration-unit.log), [build log](reports/integration-build.log), [library log](reports/integration-library.log), and [mascot results](reports/integration-visitor-results.json). Original results below are retained as history, not substituted for this run.

## Original pre-reconciliation validation

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

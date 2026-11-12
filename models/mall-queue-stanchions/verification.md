# Verification — 2026-11-12

Base: main `27321715cda338f22595076bbe7c516c3a10c863`. Work is isolated to this kit, catalog registration and focused tests. No game/UI/workflow changes, remote publication, merge or deployment performed by this worker.

- Blender 4.0.2 generated all three exports and studio thumbnails. All three `.blend` files reopened successfully with original editable parts and named module assignments (`reports/sources.json`).
- Khronos glTF Validator 2.0.0-dev.3.10: zero errors and zero warnings for each GLB. Real Three.js parsing measured bounds, local module origins, belt/socket alignment and budgets (`reports/assets.json`). All assets are below 700 KB, 20,000 triangles and at most 8 primitives.
- Unit suite: 100/100 passed, including unique layout posts, link lengths and transformed actual belt endpoint alignment. Build passed with existing large-chunk advisory. Library browser suite: 9/9 passed.
- Dedicated Chromium 156 / SwiftShader checks ran at 1440, 768 and 390 px: 10/12 passed. All three discovery cases passed with 3 decoded thumbnails and no eager GLB requests. All nine model cases consumed the expected GLB bytes and SHA-256, rendered actual geometry and exercised orbit, zoom and reset.
- **Dedicated browser suite exits 1.** Long-bay cases at 1440 and 390 px report `net::ERR_ABORTED` for their GLB request despite verified complete consumed data and rendered geometry. The strict no-request-failure assertion remains intact. No retry was used to obtain a green result, and no loader fix or failure suppression was introduced. This result is not a fully passing browser check.
- Studio images for all variants and actual model screenshots at 1440/768/390 were visually inspected: geometry present, upright, in frame, with connected belt and sockets. Selected evidence is in `reports/screenshots/`; all browser measurements and diagnostics are in `reports/browser-results.json` and `reports/browser.log`.

The unrelated game UX suite was not modified or rerun for this kit. Existing failures reported on earlier PRs are not claimed fixed. Asset-level validated metadata describes file/geometry validation, not an all-green application/browser suite. No runtime interaction behavior is claimed.

## PR #8 integration after service desk merge

Owner-approved merge of main `1363d84fc1c6426612bf4b50924f51a058be12c1` into queue feature HEAD `825b196ccb571bc5c04d1fca0e36dd628efc4e59`, 2026-11-12. Only conflict was `models/catalog.json`. Every incoming collection is preserved exactly in parsed data; the queue collection is appended. Total: 65 assets across nine collections. Queue GLBs, Blender sources, metadata, generation and test code are unchanged. No force-push, merge to main or deployment performed.

Integration checks:
- Unit: 102/102 passed. Build passed with large-chunk advisory. Library: 9/9 passed.
- Queue real-browser: 9/12 passed. `ERR_ABORTED` occurs for long bay at 1440 and 768, short bay at 768.
- Service desk real-browser: 4/6 passed. `ERR_ABORTED` at 1440 and 768.
- Essentials real-browser: 7/15 passed. `ERR_ABORTED` for bin/shelf at 1440; kiosk/lightbox/shelf at 768 and 390.
- All failures are the unchanged strict no-request-failure assertion after real model rendering/interaction and byte checks. No suppressed errors or green-seeking retries. Browser checks remain non-green.

Integration logs and JSON results are retained as `reports/integration-*`; original generation evidence remains intact. Log trailing whitespace is normalized only. Screenshots from this run remain in the isolated workspace's `integration-1363` directories.

# Verification: Mall Escalator Handrail 430

Artifact-only validation and source editing: **PASS**. Initial-base unit/build/library: **PASS**. Strict browser: **FAIL (0/3)** with old-loader `net::ERR_ABORTED`. Final integration on main after PR 12 merges: **PENDING**. Android/iOS physical hardware: **NOT TESTED**. No push, PR or deployment performed.

## Verified artifact

- Exact V2.1 P0 item 430 only. No full escalator 004, landing 429 or stationary guardrail 006.
- GLB SHA-256: `27cd23cc1d3bf33f11c114adb0be17f256e4a96e161396a541cca25734b56443`.
- 117,180 bytes; 5,100 triangles; 3,516 vertices; eight named independent meshes; five materials.
- Khronos Validator 2.0.0-dev.3.10: zero errors and zero warnings.
- Actual exported mesh topology checks: eight closed, connected, consistently wound positive-volume surfaces; belt Euler characteristic zero, other parts two.
- Actual GLB measurements: 30° central slope, 2.4 m rise, glazing/guide seating, belt clearances and pair-envelope separation. See `reports/geometry.json`.
- Reopened source and isolated real edit/reexport: belt width 80 → 90 mm and roughness 0.48 → 0.62. Other seven meshes unchanged; original source hash unchanged; edited GLB also passes Khronos 0/0.
- Six actual renders inspected, including underside and return detail. Parent independently reviewed the six-view contact sheet: studio visual PASS.
- Five focused unit tests pass. Exact future 004 integration remains NOT VERIFIED.

## Initial issues retained

The first multiview render script had an unmatched closing parenthesis and stopped before rendering. It was fixed, all Python files compiled, and the complete six-view render ran successfully. Its original failure log is retained. Early geometry review found a small unintended separation between glazing and the upper support rail; the glazing outline was corrected before the current GLB. Actual current GLB raycasts now require seating in both support rails. Initial source inspection and edit logs remain explicitly labeled initial; only the current source hash and GLB are delivery artifacts.

## Base and integration boundary

The workspace was cloned from actual GitHub main `b7421d284b503ff923508fc3046b2193108f503a`. PR 12 was still open at the last parent check. The existing loader fix is not duplicated here. Initial-base checks must not be represented as final merged-base checks, and any old-loader errors must remain failures rather than be filtered or retried to green.

Only this asset folder, its focused tests/browser harness, and one appended catalog collection are in scope. Old assets, schema, application/UI, existing evidence and download/rights policies are unchanged. Before next-batch publication, replay this unpublished asset patch on newly cloned main after PR 12 merges, then rerun all applicable gates and review the resulting diff. No Git merge or shared history rewrite is implied.

## Executed initial-base integration gates

Base: actual GitHub main `b7421d284b503ff923508fc3046b2193108f503a`; last read-only remote check still returned that commit. PR 12 remains the pending prerequisite, not part of this branch.

- `npm test`: **119/119 PASS**, no skips or cancelled tests. Repeated after the bounded display-metadata correction: **119/119 PASS**.
- `npm run build`: **PASS**, including catalog/GLB validation. Rebuilt successfully after the display correction. The existing shared JavaScript chunk warning above 500 kB remains; it is not a handrail asset warning.
- `node scripts/test-mall-escalator-handrail.mjs`: one fixed pass, **0/3 PASS** at 1440×900, 768×1024 and 390×844. Each failed the unchanged no-request-errors assertion with one GLB `net::ERR_ABORTED`. There was **no retry to green**, no error filtering and no loader/application change.
- In those three failed strict cases, complete consumed bytes matched the shipped 117,180-byte SHA-256; HTTP status was 200; nonzero WebGL draws, orbit, zoom, exact reset, exact reopen, three same-page close/reopen cycles, focus restoration, stopped render loops and no horizontal overflow all passed. These subchecks do not turn the overall failures into passes.
- `npm run test:library`: **9/9 PASS**. The existing library harness does not replace the stricter per-asset network gate.
- The source/edit verification also confirms identical normals and all four other complete material definitions, not only other mesh positions and indices.
- Preservation check: every pre-existing tracked file except the append-only catalog is byte-preserved; all old catalog entries and their order are identical. See `reports/preservation.json`.

## Actual browser visual review

The first browser images were inspected and showed the generic camera foreshortening the slope. Only the existing `display.previewRotationY` metadata changed from 0 to π/4. No geometry, material, UI, schema or camera implementation was changed. A new build and **visual-only** three-viewport capture then showed a clear sloped profile with both rounded ends, no clipping and usable framing. Canvas and page images were inspected. Original strict failure images/results remain untouched in `reports/initial-base/browser/`; corrected visual images are in `reports/initial-base/visual-corrected/`.

The visual-only capture is not a strict suite rerun or green gate. It retained an additional mobile `ERR_ABORTED` observation. The current metadata's exact reset/reopen strict matrix must be rerun on final merged main. The GLB SHA-256 stayed unchanged throughout the display correction.

Runtime: Ubuntu ARM64, Playwright 1.64.1, desktop Chromium 156.0.8078.4 with SwiftShader and viewport emulation. **Physical Android/iOS, touch hardware, Safari, GPU performance and accessibility certification remain NOT TESTED.** The legacy library report hardcodes “macOS headless”; its raw output is preserved and `reports/initial-base/runtime.json` records the actual runtime.

## Prepared local state, not final acceptance

The asset is prepared for the next batch with the strict old-base browser failures and final merged-base integration explicitly pending. Before publication: clone actual main after PR 12 merges, replay only this unpublished asset patch without Git merge/history rewriting, verify preservation and rerun Khronos, full unit/build, strict three-viewport lifecycle and library gates. Do not duplicate the pending loader fix. Exact full-escalator 004 mechanical/visual integration and real-device Android/iOS remain unverified.

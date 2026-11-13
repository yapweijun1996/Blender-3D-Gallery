# Mall batch 02 final integration · 430–439

**10 new logical types / 10 GLBs. Each local asset: PASS. Each overall status: NEEDS REVIEW.** Physical Android/iOS is NOT TESTED. Existing library demo reload failure remains unresolved. This is a draft-review candidate, not deployment approval.

Integrated on merged PR 12 main `959fbc773399478e2bfc387a33a543f66be00372`. No Git merge operation, main merge or deployment was performed. The prepared branch was preserved; only its additive asset files and ten catalog collections were replayed on fresh main.

## Per-asset gate

| ID | Type | Local source / geometry / visual / strict viewer | Overall |
| --- | --- | --- | --- |
| 430 | [Escalator handrail subsystem](../../models/mall-escalator-handrail/verification.md) | PASS; 3/3 browser viewports | NEEDS REVIEW |
| 431 | [Lift call panel](../../models/mall-lift-call-panel/verification.md) | PASS; 3/3 browser viewports | NEEDS REVIEW |
| 432 | [Lift floor indicator](../../models/mall-lift-floor-indicator/verification.md) | PASS; 3/3 browser viewports | NEEDS REVIEW |
| 433 | [Emergency exit door](../../models/mall-emergency-exit-door/verification.md) | PASS; 3/3 browser viewports | NEEDS REVIEW |
| 434 | [Fire hose reel cabinet](../../models/mall-fire-hose-reel-cabinet/verification.md) | PASS; 3/3 browser viewports | NEEDS REVIEW |
| 435 | [Sprinkler head](../../models/mall-sprinkler-head/verification.md) | PASS; 3/3 browser viewports | NEEDS REVIEW |
| 436 | [CCTV camera](../../models/mall-cctv-camera/verification.md) | PASS; 3/3 browser viewports | NEEDS REVIEW |
| 437 | [Digital advertising screen](../../models/mall-digital-advertising-screen/verification.md) | PASS; 3/3 browser viewports | NEEDS REVIEW |
| 438 | [Wayfinding ceiling sign](../../models/mall-wayfinding-ceiling-sign/verification.md) | PASS; 3/3 browser viewports | NEEDS REVIEW |
| 439 | [Food court tray station](../../models/mall-food-court-tray-station/verification.md) | PASS; 3/3 browser viewports | NEEDS REVIEW |

430 is the handrail/balustrade subsystem, **not full escalator 004**. Included context/trays do not increase the count. No physical operation, surveillance, fire-system performance, safety certification or runtime interaction is claimed. Movable parts and replaceable artwork are source-editable only.

## Accepted evidence

- [223/223 unit tests](mall-batch-02-final/accepted-unit.log), no skips; [final build](mall-batch-02-final/accepted-build.log), catalog and GLB validation.
- Strict viewer **30/30** in one fixed initial integrated pass: ten asset `browser-*` directories. Each verifies consumed bytes/SHA, HTTP200, actual drawing, orbit/zoom/reset/reopen, repeated lifecycle and unfiltered request/console/page errors. Three desktop Chromium widths: 1440, 768 and 390.
- Sprinkler approved optional underside camera/light presentation subsequently revalidated **3/3** in [sprinkler-final](mall-batch-02-final/sprinkler-final/results.json). No other model defaults changed.
- [Loading lifecycle 4/4](mall-batch-02-final/lifecycle/results.json): cancellation, rapid replacement, close/reopen and error/retry. Expected deliberately induced errors are recorded by that lifecycle harness, not confused with unexpected asset errors.
- Independent all **10 .blend reopens, 10 geometry validators and 10 real source-edit/re-export checks PASS**; see [independent evidence](mall-batch-02-final/independent/v2/independent-review.json). This is fresh validation of delivered source, not generator-only checking.
- All ten multi-angle studio sets inspected independently; actual final browser initial and alternate-angle screenshots inspected. Corrected sprinkler shows the downward yoke/bulb, not the mounting thread as its primary view. Existing default lighting for other models is subdued but geometry remains readable.
- [Seven legacy types × two widths exact pixel comparison](mall-batch-02-final/legacy-pixel-comparison.json): all **14 initial/orbit/zoom/reset screenshots byte-identical** before/after optional sprinkler presentation.
- [Preservation evidence](mall-batch-02-final/preservation.json): all prior non-catalog main files unchanged, all 80 previous catalog entries unchanged, no duplicate IDs, total90; historic reports preserved byte-for-byte. Ten GLBs total 2,918,096 bytes. Existing rights and disabled public downloads remain unchanged; no public redistribution license invented.

## Failures and limits, not hidden

**Library suite is NOT GREEN:** candidate [log](mall-batch-02-final/library.log) records seven PASS cases, then the legacy demo refresh case times out after30s at `test-library-browser.mjs:211` waiting for `domcontentloaded`; final reflow case is not run. A separate fixed one-pass pristine-main run reproduced the exact failure: [baseline log](mall-batch-02-final/library-baseline/library.log), [results](mall-batch-02-final/library-baseline/library/results.json). The existing-baseline failure is established; its root cause is not proven. No test was weakened and no retry-to-green claimed. Raw library environment wording says macOS, but actual executor was Ubuntu ARM64, desktop Chromium156.0.8078.4 / SwiftShader.

Historic initial prepared strict results (10/30 across separate old-loader runs) remain unchanged. Merged-main 30/30 supersedes them for current loading behavior without erasing them. The source-review initial attempt lacked Blender headless configuration; its startup failures are retained alongside the corrected successful headless run.

The initial sprinkler metadata test rejected the two newly approved display keys; [failed unit log](mall-batch-02-final/final-unit.log) is preserved. Its exact-key contract was updated to require both specific approved values, not relaxed, then all223passed.

The reused original PR12 preview harness expected the ceiling panel to **change**; here it correctly stayed unchanged, so two purpose-specific assertions, inapplicable to this unchanged baseline and not asset failures, fail in [raw candidate log](mall-batch-02-final/preview-candidate.log). No original harness was changed. Independent exact-hash comparison of all14captures proves unchanged old appearance; all unexpected-error lists are empty. These are not presented as a14/14pass of that original harness.

Physical Android/iOS browsers, mobile GPUs and touch devices are **NOT TESTED**. Viewport emulation is not native device acceptance. Overall per-type NEEDS REVIEW persists. Current Pages workflow runs npm ci/build but does not enforce unit, library or browser gates; a successful Pages run is not acceptance evidence. No merge/deployment authorization is inferred.

## Diff review

Authored source, tests, metadata and documentation pass whitespace checking. Whole-diff warnings are confined to preserved raw test/build logs (Vite trailing spaces and raw blank lines). They were not sanitized because original evidence must remain unchanged. No existing application code, workflow or original test was edited; the new sprinkler exact contract explicitly requires its approved camera/light values.

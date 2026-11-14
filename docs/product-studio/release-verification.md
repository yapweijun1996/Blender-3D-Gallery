# Product Studio verification

Local candidate tested against base `5fd5401c910a7784c2691e8e0693046f4c007e52`. Local evidence is not a remote CI or deployment claim.

- Unit: 504/504 PASS.
- Full suite: all entries in `evidence/canvas-fix-final/status.txt` exited 0.
- Product Studio: 15 browser scenarios PASS using the actual registered 186,016-byte GLB.
- Game: unchanged original rapid touch UX passes; responsive 12-viewport matrix passes.
- Touch negatives: five groups PASS (cancel, inspection pinch/orbit, keyboard and single activation, noncanvas scrolling, lifecycle disposal).
- Existing Game/PWA/Solar/library and both GJH can suites remain PASS.
- Existing 431 catalog records remain byte-equivalent as parsed objects; only original Demo Food Tin added.
- Physical Android/iOS and shipping Safari remain NOT TESTED. Chromium viewport/touch emulation is not hardware testing.

## Touch defect and bounded repair

The original rapid UX fixture failed on both the unchanged baseline and candidate before the fix. Its enabled button received pointer/touch down/up, but no native click. Browser input trace showed a native fling followed by tap suppression. The original trace has six `FilterTapSuppression` events; the fixed trace has zero, with zero fling-start/handling events. Compressed traces and the hash/count comparison are retained.

The repair cancels native `touchstart` only when the target is the Game canvas, which already owns gestures through `touch-action:none`. Pointer-based game/inspection interaction remains active. It does not intercept outside touches, synthesize clicks, alter button dispatch, weaken assertions, or replace the original UX fixture. Negative tests confirm pinch/orbit, scrolling outside canvas, keyboard, cancel and listener disposal remain functional.

Chromium's [TapSuppressionController source](https://chromium.googlesource.com/chromium/src/+/refs/tags/133.0.6925.1/components/input/tap_suppression_controller.h) describes suppression following a tap that cancels a fling; this supports the observed trace interpretation, not a claim about all browser implementations.

## Publication gate and rollback

The Pages workflow now installs the pinned Playwright runtime and runs the fixed unit/browser gate before artifact upload. Deployment depends on successful build job completion. CI budget: 90 minutes; local complete suite approximately 25 minutes. A failure does not deploy this candidate.

After push, verify the actual Actions conclusion, Pages deployment and live Product Studio asset SHA. If a deployed release needs rollback, revert its commit to preserve history and pass the same release gate. Never force-push or claim pending CI as successful.

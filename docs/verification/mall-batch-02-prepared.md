# Mall batch 02: prepared, NOT FINAL

**Ten exact V2.1 P0 types (430–439), ten GLBs. Local asset preparation: PASS. Final merged-base integration and second-batch quality gate: PENDING. Physical Android/iOS: NOT TESTED.**

Prepared asset chain ends at `c629aaaa066d190f5acd1c26c689d5dca944dd9c`. This document summarizes existing evidence only. Earlier models are not counted, and included trays or other context do not add model types.

## Per-type evidence

All ten local geometry, editable-source and render checks passed. Strict counts below are historical initial-base runs, not a fresh combined final run.

| V2.1 ID | Type and verification | Local geometry/source/render | Initial strict viewer |
| --- | --- | --- | --- |
| 430 | [Mall Escalator Handrail](../../models/mall-escalator-handrail/verification.md) | PASS | 0/3 |
| 431 | [Mall Lift Call Panel](../../models/mall-lift-call-panel/verification.md) | PASS | 3/3 |
| 432 | [Mall Lift Floor Indicator](../../models/mall-lift-floor-indicator/verification.md) | PASS | 2/3 |
| 433 | [Mall Emergency Exit Door](../../models/mall-emergency-exit-door/verification.md) | PASS | 0/3 |
| 434 | [Mall Fire Hose Reel Cabinet](../../models/mall-fire-hose-reel-cabinet/verification.md) | PASS | 0/3 |
| 435 | [Mall Sprinkler Head](../../models/mall-sprinkler-head/verification.md) | PASS | 1/3 |
| 436 | [Mall CCTV Camera](../../models/mall-cctv-camera/verification.md) | PASS | 1/3 |
| 437 | [Mall Digital Advertising Screen](../../models/mall-digital-advertising-screen/verification.md) | PASS | 1/3 |
| 438 | [Mall Wayfinding Ceiling Sign](../../models/mall-wayfinding-ceiling-sign/verification.md) | PASS | 0/3 |
| 439 | [Mall Food Court Tray Station](../../models/mall-food-court-tray-station/verification.md) | PASS | 2/3 |

The arithmetic total is **10/30 across different initial runs**, **not a combined final pass**. All recorded strict failures retain the existing-loader `net::ERR_ABORTED` evidence. No error filtering, retry-to-green, history erasure or duplicate loader fix changes those outcomes. Desktop Chromium viewport emulation is not physical mobile acceptance.

## Latest current-base checks and upstream state

The 439 preparation ran **172/172 full unit tests**, production build/catalog validation and **9/9 library browser checks**, all passing. This does **not** mean all strict viewer tests are green. See its [verification](../../models/mall-food-court-tray-station/verification.md), [gate exit codes](../../models/mall-food-court-tray-station/reports/gate-exitcodes.json), [unit log](../../models/mall-food-court-tray-station/reports/unit-full.log), [build log](../../models/mall-food-court-tray-station/reports/build.log) and [strict results](../../models/mall-food-court-tray-station/reports/browser/results.json).

At the [latest upstream check](../../models/mall-food-court-tray-station/reports/upstream-final.txt):

- Main: `b7421d284b503ff923508fc3046b2193108f503a`.
- Existing [PR 12](https://github.com/yapweijun1996/Blender-3D-Gallery/pull/12): open/unmerged, head `04d31c694520a0935a6c0e65b737bd91f43a8bc6`.
- The unmerged first-batch implementation was not copied into this preparation. Only the existing `previewRotationY` presentation field is used.
- Final merged-base integration and second-batch quality gate remain **PENDING**. Physical Android and iOS remain **NOT TESTED**.

All raw per-asset history, including failures, is preserved. Existing rights and disabled public downloads are unchanged. These are illustrative assets, not safety or engineering certifications; source poses do not imply runtime controls. This preparation and summary performed no push, new PR, merge or deployment. No new tests were run solely for this documentation-only summary.

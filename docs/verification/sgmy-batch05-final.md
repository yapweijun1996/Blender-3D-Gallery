# SG/MY batch 05 · 10 independent assets

**Each asset: local PASS; overall NEEDS REVIEW because physical Android/iOS is NOT TESTED.** Ten new V2.1 types:320 and361–369. Reused context does not count as additional types. This is review evidence, not deployment approval.

Based on current main `2d8f7731fc7f9a01b77172780f3e31aa54228ad3`. Both producer batches were added in an isolated checkout without merging branches or changing shared history. No push, PR, main merge or deployment was performed by this assembly step.

| ID | Asset | GLB bytes | Local source / geometry / visual / viewer | Overall |
| --- | --- | ---: | --- | --- |
| 320 | [HDB Drop-Off Porch](../../models/hdb-drop-off-porch/verification.md) | 80,000 | PASS; 3/3 strict viewports | NEEDS REVIEW |
| 361 | [Hawker Stall Roller Shutter](../../models/hawker-stall-roller-shutter/verification.md) | 183,256 | PASS; 3/3 strict viewports | NEEDS REVIEW |
| 362 | [Hawker Stall Exhaust Hood](../../models/hawker-stall-exhaust-hood/verification.md) | 228,852 | PASS; 3/3 strict viewports | NEEDS REVIEW |
| 363 | [Hawker Stall Stainless Counter](../../models/hawker-stall-stainless-counter/verification.md) | 121,732 | PASS; 3/3 strict viewports | NEEDS REVIEW |
| 364 | [Hawker Stall Queue Sign](../../models/hawker-stall-queue-sign/verification.md) | 69,688 | PASS; 3/3 strict viewports | NEEDS REVIEW |
| 365 | [Hawker Stall Number Plate](../../models/hawker-stall-number-plate/verification.md) | 95,568 | PASS; 3/3 strict viewports | NEEDS REVIEW |
| 366 | [Hawker Centre Ceiling Fan](../../models/hawker-centre-ceiling-fan/verification.md) | 31,044 | PASS; 3/3 strict viewports | NEEDS REVIEW |
| 367 | [Hawker Centre Table Number](../../models/hawker-centre-table-number/verification.md) | 100,512 | PASS; 3/3 strict viewports | NEEDS REVIEW |
| 368 | [Hawker Centre Tray Rack](../../models/hawker-centre-tray-rack/verification.md) | 319,088 | PASS; 3/3 strict viewports | NEEDS REVIEW |
| 369 | [Kopitiam Coffee Sock](../../models/kopitiam-coffee-sock/verification.md) | 47,852 | PASS; 3/3 strict viewports | NEEDS REVIEW |

## Combined gate

- [235/235 units](sgmy-batch05-final/final-unit.log), no skips. [Build and catalog/Khronos validation PASS](sgmy-batch05-final/final-build.log).
- Strict real-GLB viewer **30/30 PASS** in one fixed combined gate: [first five /15](sgmy-batch05-final/browser-a/results.json), [365](sgmy-batch05-final/browser-hawker-stall-number-plate/results.json), [366](sgmy-batch05-final/browser-hawker-centre-ceiling-fan/results.json), [367](sgmy-batch05-final/browser-hawker-centre-table-number/results.json), [368](sgmy-batch05-final/browser-hawker-centre-tray-rack/results.json), [369](sgmy-batch05-final/browser-kopitiam-coffee-sock/results.json). Each consumes exact bytes/SHA, verifies HTTP200, actual drawing, orbit/zoom, reset/reopen and repeated lifecycle, stopped rendering, focus return, disabled downloads, no overflow and no unexpected request/console/page errors. No filtering or retries to green.
- [Loading lifecycle4/4](sgmy-batch05-final/lifecycle/results.json) and [library9/9](sgmy-batch05-final/library/results.json) PASS. This fixed batch05 library result does not erase or establish a fix for failures observed in other batches.
- Independent [all ten delivered .blend reopens](sgmy-batch05-final/independent-review/reopen.json) PASS: metre scale, finite mesh coordinates, no linked libraries, source hashes unchanged. Original-source edit/re-export proofs exist for all ten in asset reports. Assembly independently repeated five source-edit/geometry checks for320/361–364 in separate fixtures and additionally reopened those saved edited .blend files; [reopened exports are byte-identical](sgmy-batch05-final/reopened-edit-proof-a.json). Original reports were not overwritten.
- All ten multi-angle studio preview sets inspected, plus all30 actual Gallery initial screenshots across the three tested widths; independent [final review](sgmy-batch05-final/independent-review/independent-review.json) PASS. [Final contact sheet](sgmy-batch05-final/final-browser-contact.webp). Hood filters and ceiling fan underside are shown using the already approved optional per-model view/light settings. No runtime fan motion or exhaust simulation is claimed.
- [Old-default regression](sgmy-batch05-final/legacy-preview-comparison.json): pristine main baseline14/14 and candidate14/14; seven existing types × two widths × initial/orbit/zoom/reset/reopen = **70 exact unchanged image hashes**. The original preview harness runs without its historical PR12-specific ceiling-change comparison; independent comparison here correctly requires every old model to remain unchanged.
- [Preservation](sgmy-batch05-final/preservation.json): all100 existing catalog entries unchanged,110 total, no duplicates; all previous non-catalog tracked files unchanged;356 producer historical report/evidence files byte-identical. Ten GLBs total **1,277,592 bytes**. No existing model replaced.

## Scope, provenance and limits

Each model includes independent Blender Python generator, editable `.blend`, optimized `.glb`, multi-angle previews, metadata, attribution/rights and evidence. Four small365/366/367/369 props are within100KiB/3000triangles; rack368 is within400KiB/10000triangles.320/361–364 use their documented complexity-specific budgets.

The wall stall number plate and table tent are distinct types. The tray rack reuses the already-created439 tray profile as uncounted context. Existing owner-project reuse rights, bundled Bfont attribution and disabled public downloads are retained; no public redistribution license is invented. Counter/shutter illustrative assembly evidence records450mesh pairs and zero penetrations, not installation or structural certification.

These are static visual modules. Source-editable blades, labels, panels, trays and cloth do not imply runtime controls, operating machinery, live signage, electrical/hygiene/engineering/safety certification or simulations. The coffee sock is intentionally simple modeled cloth with an open top, not cloth physics.

Actual environment: Ubuntu ARM64, desktop Chromium156.0.8078.4 / SwiftShader;1440×900,768×1024 and390×844 viewport emulation. Physical Android/iOS devices, native mobile browsers/GPUs and touch behavior are **NOT TESTED**. The raw library harness has inherited macOS wording; that label is not the actual executor. Every overall per-asset result therefore remains NEEDS REVIEW. Current Pages workflow build success is not comprehensive test or real-device acceptance. No unverified deployment authorized.

Historic producer logs, including preliminary checks and pending-at-the-time statements, remain unchanged; this report is the current combined-gate result. Final metadata now points to this result without rewriting those records. Authored files pass whitespace checks; raw test/build log whitespace is preserved.

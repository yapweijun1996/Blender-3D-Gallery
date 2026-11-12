# Optional per-model preview camera and light configuration

## Bounded behavior

The owner approved optional display settings to correct the ceiling presentation.
Only the existing Gallery camera direction and two existing light intensities/key
position are overridable. [Schema, limits and omission policy](../assets.md#optional-gallery-preview-settings-implemented).
No UI redesign, material/geometry transformation, source regeneration, new light
object, transport change, or Game/Solar scene change is included. Ceiling remains
non-downloadable and its overall asset gate remains NEEDS REVIEW; this is not a
publication or physical-device signoff.

Ceiling configuration: camera direction `[1,-1.4,1]`, key position `[4,-7,5]`.
The actual initial canvases at 1440 and 390 px show the decorative off-white
underside, four recessed panels, grid and suspension pieces without clipping.
The original underside was substantially darker. The camera is not faked by
rotating the model; GLB and Blender source bytes remain unchanged.

- [Before initial](../../output/playwright/preview-config/baseline-mall-ceiling-panel-module-1440-initial.png)
- [Before underside orbit](../../output/playwright/preview-config/baseline-mall-ceiling-panel-module-1440-underside.png)
- [After initial](../../output/playwright/preview-config/candidate-mall-ceiling-panel-module-1440-initial.png)
- [After narrow initial](../../output/playwright/preview-config/candidate-mall-ceiling-panel-module-390-initial.png)

## Verification

Baseline source: `7a69dd674d5b3ad10739187e01a4f5a491c2cde8`. Ubuntu/Linux ARM64,
Node 22, Playwright Chromium 156.0.8078.4 and SwiftShader; desktop viewport
emulation only. Physical Android and iOS: **NOT TESTED**.

- [Baseline](../../output/playwright/preview-config/baseline.json) and
  [candidate](../../output/playwright/preview-config/candidate.json): 14/14 cases
  each. Pool table, Ball 08, Earth, Saga, floor tile and railing post have exactly
  identical baseline/candidate PNG hashes for initial, keyboard orbit, keyboard
  zoom and reset at 1440×900 and 390×844. This covers every existing default camera
  branch plus ordinary mall assets. The ceiling changes intentionally; initial,
  reset and reopen match exactly at both widths. Full screenshots retained locally;
  representative before/after initials are stored alongside these reports.
- [Ceiling strict suite](../../output/playwright/preview-config/ceiling.json): 3/3,
  adding 768×1024. Source GLB byte length and SHA-256 match consumed browser bytes,
  WebGL draws occur, orbit/zoom/reset work, download stays hidden and no horizontal
  overflow occurs. All request, console, page and HTTP errors are checked, with
  no request-failure filtering. Reset assertion is stronger than before: exact
  equality with the initial view, not merely inequality with the zoomed image.
- [Loading lifecycle](../../output/playwright/preview-config/lifecycle.json): 4/4,
  including real partial-transfer cancellation/reopen and 503, truncated GLB and
  transport-failure retry. Only explicitly injected failures/abort are expected.
- [Library](../../output/playwright/preview-config/library.json): 9/9, including
  static lazy loading, navigation/history, repeated viewer/demo opening and
  resource release. Its inherited macOS label is historical harness text, not
  actual execution; `executedEnvironment` records the Ubuntu run.
- All 132 unit tests pass, including malformed/non-finite/out-of-range/degenerate
  preview values, valid boundary values, partial/omitted settings and preserved
  unknown fields. Asset validation/build pass. Existing >500 kB shared-chunk
  warning remains. No configured lint/typecheck command exists in package.json.
- [Source/build manifest](../../output/playwright/preview-config/verification.json)
  proves all built GLBs match the frozen baseline and ceiling source/export are
  byte-identical. Source syntax checks and `git diff --check` pass.

## Findings retained, not hidden

The first baseline run exposed a pre-existing Saga 390 px reset-fit difference
from its initial view. It is [retained](../../output/playwright/preview-config/initial-baseline-failure.json),
not fixed in this bounded change. Comparison now requires every corresponding
candidate state to match baseline exactly, including that reset state.

Strengthening the older ceiling suite initially compared a keyboard-focused
canvas against a pointer-reset canvas, so CSS `:focus-visible` changed the image
border despite identical interior pixels. Merely focusing again did not normalize
input modality. Both [first](../../output/playwright/preview-config/focus-fixture-failure.json)
and [second](../../output/playwright/preview-config/focus-visible-fixture-failure.json)
failed reports remain. The final harness blurs the canvas consistently before
**every** screenshot, without cropping/masking pixels or suppressing errors.

## Reproduce

Freeze the baseline build before applying the change, then use fresh output
paths; the comparison harness refuses to overwrite prior evidence.

```sh
npm run build
node scripts/test-preview-config.mjs /path/to/frozen-baseline /tmp/preview-before
node scripts/test-preview-config.mjs dist /tmp/preview-after /tmp/preview-before
npm test
MALL_QA_DIR=/tmp/ceiling-preview node scripts/test-mall-ceiling-panel.mjs
TEST_ARTIFACT_DIR=/tmp/preview-loading node scripts/test-gallery-loading.mjs
TEST_ARTIFACT_DIR=/tmp/preview-library npm run test:library
```

Local work only. No remote push, PR, merge or deployment was performed.

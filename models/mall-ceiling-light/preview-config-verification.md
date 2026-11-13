# Ceiling Light 423: approved preview integration

## Result

The gallery now starts on the light's decorative underside. The frame and four corner fasteners are readable at 1440×900, 768×1024 and 390×844 without clipping. Initial, reset and reopened canvas PNGs match exactly at every viewport. The source and exported geometry were not inverted or regenerated.

**Overall asset gate remains NEEDS REVIEW:** physical Android/iOS and native touch/GPU performance are not tested. This is a local presentation correction, not publication or installation/lighting certification.

The approved optional-display implementation was locally cherry-picked from commit `aff9c12c40430f7c777ad5b69b16ff2832c46cc8` onto asset commit `bc1ee861264c2b7bb9a10316741060ee6999297e`, producing `5d25f427622e62be604bb28c2752011d94282570`. No Git merge, remote push, PR or deployment occurred.

## Configuration and scope

Only these supported lamp metadata overrides were added:

```json
{
  "previewCameraDirection": [1, -1.4, 1],
  "previewLighting": {"directionalPosition": [4, -7, 5]}
}
```

Existing previewRotationY remains zero. Hemisphere/key intensities retain their defaults. No material, mesh, source, export, animation, UI or transport changes were made by the lamp integration. The pre-existing key light is repositioned for preview readability; the fixture's static emissive material **does not illuminate neighbouring Three.js geometry**. There is no implemented switch, bloom or photometric model.

## Executed checks

All evidence is separate from the original asset report, under [reports/preview-config](reports/preview-config/).

| Check | Result | Evidence |
| --- | --- | --- |
| Full Node unit suite | PASS, 137/137 | unit.log |
| Catalog asset validation + production build | PASS | build.log |
| Lamp strict viewer | PASS, 3/3 | lamp.json |
| Ceiling 422 strict viewer | PASS, 3/3 | ceiling.json |
| Library regression | PASS, 9/9 | library.json |
| Load/cancel/retry lifecycle | PASS, 4/4 | lifecycle.json |
| Original-baseline preview comparison | PASS, 14/14 | comparison.json |
| Source/export/pre-config evidence preservation | PASS, 176 files byte-identical | preservation.json |
| Built catalog GLBs | PASS, all 74 catalog exports match built bytes | preservation.json |
| Actual initial screenshot inspection | PASS at all three lamp widths; ceiling narrow also inspected | *-initial.png |
| Physical Android / iOS | NOT TESTED | No device evidence |

The lamp suite checks exact SHA-256 and byte length for both first load and reopen, HTTP 200 for every GLB response, positive WebGL draws, title, hidden download, orbit/zoom, exact reset, an additional orbit, close/reopen, and absence of horizontal overflow. All requestfailed, console, page and HTTP errors are collected without filtering. Final error arrays are empty.

Before every full-canvas screenshot, the canvas is blurred consistently to remove keyboard-versus-pointer focus-modality differences. A 350 ms wait lets controls settle. No cropping, pixel masking or error suppression is used. Initial/reset/reopen hashes are retained in lamp.json.

The 14-case comparison covers pool table, Ball 08, Earth, Saga, floor tile, railing post and ceiling at desktop/narrow widths. All six unconfigured models retain byte-identical initial/orbit/zoom/reset screenshots against the original pre-configuration baseline. The ceiling changes intentionally. The previously documented Saga narrow reset-fit difference remains unchanged and is not concealed or fixed here. Lamp coverage is provided separately by the stronger three-viewport suite.

The lifecycle suite deliberately injects partial-transfer cancellation, HTTP 503, truncated GLB and transport aborts. Only its explicit injected failures are expected. No lifecycle test behavior was changed.

## Pixel inspection and preservation

The lamp's warm off-white diffuser is visible immediately, surrounded by a readable grey-ivory frame with four small dark fasteners. It fits all three viewports with margin. The configured ceiling narrow screenshot shows its four mineral-fibre-style panels and grid from below. Emission brightness is not evidence of real scene illumination.

Original rear/underside screenshots remain in [reports/browser](reports/browser/), and the complete [pre-configuration verification](verification.md) is retained. All old source/GLB files and all original lamp report files compare byte-for-byte with the asset commit. Current GLB SHA-256 is unchanged:

`b8b0b31c7657028dff44f8c04ba7e65b07feac892b4849b81bb0a1fd78432cf8`

Source SHA-256 is unchanged:

`881ff73ec593c8c96bc19e3eebf0a7f4f085fe43655304cd0788abdf977e68bd`

Execution: Ubuntu/Linux ARM64, Node v22.23.3, Chromium 156.0.8078.4, headless SwiftShader. Library's inherited macOS text is not macOS evidence; the actual environment is recorded in preservation.json. Existing Vite large-shared-chunk warning remains. Captured logs normalize trailing whitespace only. No integration test failed; an additional first-load hash assertion was added after the complete pass and the full strict lamp suite was rerun successfully.

## Reproduce

Use fresh evidence directories so historical captures remain intact.

```sh
npm test
npm run build
MALL_QA_DIR=/fresh/lamp node scripts/test-mall-ceiling-light.mjs
MALL_QA_DIR=/fresh/ceiling node scripts/test-mall-ceiling-panel.mjs
TEST_ARTIFACT_DIR=/fresh/library npm run test:library
TEST_ARTIFACT_DIR=/fresh/lifecycle node scripts/test-gallery-loading.mjs
node scripts/test-preview-config.mjs dist /fresh/comparison /path/to/baseline-directory
```

The comparison baseline directory must contain results.json copied from the preserved output/playwright/preview-config/baseline.json. Public download remains false; redistribution terms remain unspecified.

# 435 verification · prepared local state

**Local asset/source: PASS. Overall integration: NEEDS REVIEW.** Physical Android/iOS: **NOT TESTED**. Final merged-base gate: **PENDING**.

## Base and scope

Prepared on exact local chain base `1cbbfac99c3400a098846032a19516fb321c7f69`, preserving prepared items 430–434. Canonical main was rechecked before initial browser gates and after them: `b7421d284b503ff923508fc3046b2193108f503a`, unchanged. PR #12 remains open, draft and unmerged at head `04d31c694520a0935a6c0e65b737bd91f43a8bc6`.

Only V2.1 P0 **435 Mall Sprinkler Head** is added. No unmerged first-batch implementation, app/viewer/schema change, runtime activation or simulation. Existing `previewRotationY` only.

## Executed local gates

| Gate | Result |
| --- | --- |
| Blender 4.0.2 generation and delivered source reopen | PASS |
| Khronos glTF Validator | **0 errors / 0 warnings** |
| Metric dimensions, 13 independent mesh modules, downward orientation | PASS |
| Actual source manifold edges / degenerate faces / signed volume | PASS: 0 / 0 / positive for all 13 |
| Above-plane mesh envelope inside 15 mm context opening radius | PASS: approximately 1 mm minimum radial gap |
| Isolated bulb radial mesh +15% and copied amber material, save/reopen/re-export | PASS; 12 other meshes and all transforms unchanged |
| Edited GLB validation | 0 errors / 0 warnings |
| Focused unit contracts | **6/6 PASS** |
| Full repository units | **147/147 PASS** |
| Build and all 74 catalog GLBs | PASS |
| Library browser suite | **9/9 PASS** |
| One strict three-viewport pass | **1/3 PASS, 2/3 FAIL** |

Optional Draco library is absent; the exported GLB needs no decoder. Build retains the existing >500 kB JavaScript chunk warning. No unrelated app optimization was attempted.

The first authoring invocation omitted Blender's background flag and exited before starting with an X11 display error. Inspection confirmed no source/export existed; the corrected headless generation succeeded. This was a preparation-command error, not a browser retry. The raw strict browser run was never retried.

## Exact asset and image review

- SHA-256: `ef2045874b59e7e60c35976b23d8b2fce2694cfb8f575222373c9931b17994ca`.
- **70,796 bytes / 2,752 triangles / 1,870 vertices / 13 primitives / four materials**.
- `dist/assets/optimized-CT3r8pwJ.glb` matches the source export byte-for-byte.
- Dimensions: glTF X/Y/Z **0.066 × 0.071 × 0.066 m**.
- Ceiling-plane origin glTF Y=0. Fitting above plane 0.019 m; pendant below plane 0.052 m.
- Six 768 × 768 PNG masters and six decoded WebPs inspected. WebPs range 10,096–22,754 bytes.
- 35 strict-browser PNGs inspected through three complete contact sheets, plus the full 390px page. The 16 library screenshots were also reviewed.

Parent independently inspected the hero, underside and 390px initial browser image and accepted the prepared local visual result. This is not merged-base acceptance.

The opaque glossy red bulb remains visible in the source previews and browser. It is not physical glass, and neither refraction nor temperature encoding is claimed. The old camera looks down onto the ceiling trim and partly hides the yoke. Correct downward geometry was preserved, with separate underside/ceiling-context renders. No model inversion or new camera schema was used.

## One strict initial-base browser run

Actual environment: **Ubuntu arm64, Desktop Chromium 156.0.8078.4, headless SwiftShader**, desktop viewport emulation only. Raw files are in `reports/browser-initial-base/`. No request/console error filtering, duplicate-loader fix or retry-to-green. Only trailing line whitespace in text logs was normalized for the Git whitespace check; recorded failures are unchanged.

| Viewport | Functional observations | Unfiltered unexpected errors | Strict result |
| --- | --- | --- | --- |
| 1440 × 900 | Exact bytes/SHA; HTTP 200; all functional checks below pass | 1 × net::ERR_ABORTED | FAIL |
| 768 × 1024 | Same | None | PASS |
| 390 × 844 | Same | 1 × net::ERR_ABORTED | FAIL |

All three: real drawing; changed orbit/zoom pixels; exact initial/reset/reopen pixel equality; three same-page close/reopen cycles; stopped drawing after close; restored card focus; no horizontal overflow. All observed GLB responses were HTTP 200. There were no unexpected console/page exceptions. The two strict failures are the preserved old-loader request aborts, so this is **not a green browser gate**.

Library: 9/9 pass, raw `reports/library-initial-base/results.json` and screenshots preserved. The inherited library test hardcodes a “macOS headless” label; actual execution was Ubuntu, as recorded in `reports/actual-environment.json`. This incorrect old label was not silently edited and does not imply macOS hardware testing.

## Preservation and disposition

`reports/preservation.json` verifies all **73 old assets**, old collection objects and the old catalog byte prefix unchanged. The new catalog has **74 assets**. No old source, app, UI or schema files changed. Catalog formatting outside the appended entry was restored before the final unit/build check; semantic catalog data was identical to that consumed during the one strict browser pass.

This is a prepared local asset, not a release or merged-base acceptance. **No temperature rating, flow, fire protection, installation or certification claims. No activation or simulation.** The ceiling opening/clearance is a visual context check, not equipment guidance.

Downloads remain disabled under the existing rights statement. No remote push, PR, merge, history rewrite or deployment was performed. Final merged-base integration remains **PENDING / NEEDS REVIEW**; physical Android/iOS **NOT TESTED**.

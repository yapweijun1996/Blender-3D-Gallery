# 436 verification · prepared local state

**Local asset/source: PASS. Overall integration: NEEDS REVIEW.** Physical Android/iOS: **NOT TESTED**. Final merged-base gate: **PENDING**.

## Scope and base

Only exact V2.1 P0 **436 Mall CCTV Camera** is added, as an original visible static scene prop. No actual video capture, network, tracking, hidden surveillance, deployment or operating instructions. Source pan/tilt pose edits are geometric authoring only, not runtime controls. Lens is opaque and makes no physical optics claim.

New isolated local branch started from `f59c3af5b544731985eb57050069fc2b41db006c`, preserving items 430–435. Canonical main was checked initially, before browser gates and after them: `b7421d284b503ff923508fc3046b2193108f503a`, unchanged. PR #12 was still open, draft and unmerged at `04d31c694520a0935a6c0e65b737bd91f43a8bc6`. Its unmerged implementation was not imported. No app/viewer/schema changes or new preview fields. Existing `previewRotationY` only.

## Executed gates

| Gate | Result |
| --- | --- |
| Blender 4.0.2 deterministic generation and actual delivered source reopen | PASS |
| Khronos glTF Validator | **0 errors / 0 warnings** |
| 13 independent mesh modules, metre dimensions, source pivot hierarchy and anchor | PASS |
| Actual source topology | 0 nonmanifold edges, 0 degenerate faces; positive signed volumes |
| Continuous head swept-cylinder clearance bound from actual source vertices | PASS: 3.0 mm yoke-side gap, 6.23 mm bridge gap |
| Actual source triangle-overlap checks | PASS: 20 pan/tilt poses; 0 checked overlap pairs |
| Real lens geometry/material and pan/tilt pose edit, saved/reopened/re-exported | PASS |
| Edited GLB validator | 0 errors / 0 warnings |
| Focused unit contracts | **6/6 PASS** |
| Full repository unit tests | **153/153 PASS** |
| Build and 75 catalog GLBs | PASS |
| Library browser suite | **9/9 PASS** |
| Single strict three-viewport pass | **1/3 PASS, 2/3 FAIL** |

Intentional axle-to-housing mating contact is excluded from overlap checks. These are visual geometry checks, not mechanical, installation or safety specifications. The 20 sampled poses use pan 0/40/90/180/270 degrees and tilt -30/0/20/45 degrees. Separate source-vertex envelope checks conservatively bound continuous tilt clearance.

The actual isolated source edit enlarged only the lens mesh radius by 10%, assigned an independent opaque blue lens material, set pan to 40 degrees and tilt to 45 degrees, saved/reopened the edited Blender file and exported without regeneration. All 12 other mesh-coordinate arrays stayed identical. Mesh-local transforms and pivot anchors were preserved within 1e-7, with maximum observed export-rounding delta 1.49e-8. The delivered source hash stayed unchanged. The initial verifier used strict float equality and exposed that export round-off; the test now uses this explicitly measured tolerance. It did not suppress a geometric failure or change any browser gate.

Optional Draco library is absent; this GLB needs no decoder. Build retains the existing >500 kB JavaScript chunk warning. No unrelated app optimization was attempted.

## Exact asset and pixel review

- SHA-256: `a58ca329bed430d307884ebe190673d40f1cadc282dac45773ee632d3d3e433b`.
- **101,568 bytes / 2,572 triangles / 3,584 vertices / 13 primitives / 4 materials**.
- No textures, animations, cameras, lights or external GLB buffers.
- `dist/assets/optimized-DKKAIeby.glb` matches the exported bytes exactly.
- glTF X/Y/Z dimensions: **0.140 × 0.148754 × 0.140 m**.
- Mount plane glTF Y=0; tilt-pivot centre Y=-0.098 m; default downward tilt 20 degrees.
- Seven 768 × 768 PNG masters and seven decoded WebPs: hero, front, side, mount, underside, alternate source pose and ceiling context. WebPs are 7,056–18,972 bytes. Ceiling slab appears only in studio context, not in the GLB.
- All seven studio views, seven WebPs, all 35 strict-browser screenshots through complete contact sheets, full 390px page, and 16 library screenshots inspected.
- Parent independently inspected the exact hero and 390px initial browser image and accepted the recognizable camera/lens/mount and unclipped local visual result. This is prepared-local acceptance only, not merged-base acceptance.

A bounded visual-authoring refinement before browser testing reduced studio overexposure, clarified the dark lens and removed coplanar yoke overlap. No refinements or asset changes followed the accepted final visuals. Existing gallery lighting/camera were left unchanged; source and browser views remain recognizable.

## One strict initial-base browser run

Actual environment: **Ubuntu arm64, Desktop Chromium 156.0.8078.4, headless SwiftShader**, viewport emulation only. Raw results: `reports/browser-initial-base/results.json` and `reports/browser-run.log`.

| Viewport | Functional checks | Unfiltered unexpected errors | Strict result |
| --- | --- | --- | --- |
| 1440 × 900 | All pass | None | PASS |
| 768 × 1024 | All pass | 1 × net::ERR_ABORTED | FAIL |
| 390 × 844 | All pass | 1 × net::ERR_ABORTED | FAIL |

All three consumed the exact exported SHA/byte count, all observed GLB responses were HTTP 200, real drawing occurred, orbit and zoom changed pixels, reset/reopen restored exact initial pixels, three same-page close/reopen cycles passed, closing stopped rendering, focus returned to the card, and no horizontal overflow occurred. No unexpected console/page exceptions occurred. The two failures are retained old-loader request aborts, so this is **not a green browser gate**. No request filtering, duplicate-loader fix or retry-to-green.

Library passed 9/9. The existing library test hardcodes an incorrect “macOS headless” label; the actual Ubuntu environment is recorded separately in `reports/actual-environment.json`. This is not macOS or native-mobile testing. The library command initially used an unrecognized output-directory environment variable, so its single run wrote to its existing default temporary directory; all result/screenshot modification times were checked against this run and copied into `reports/library-initial-base/`. No library rerun was used. For reproduction, set `TEST_ARTIFACT_DIR`, not `LIBRARY_QA_DIR`.

## Preservation and disposition

`reports/preservation.json` verifies all **74 old assets**, old collection objects and the old catalog byte prefix unchanged. The new catalog contains **75 assets**. The only modified pre-existing tracked file is the catalog append. No old asset/source/app/UI/schema bytes changed.

Downloads remain disabled under the existing rights statement. No public redistribution license was invented. No remote push, PR operation, merge, shared-history rewrite or deployment occurred. This remains a prepared local asset, **final merged-base PENDING / overall NEEDS REVIEW**, with physical Android/iOS **NOT TESTED**.

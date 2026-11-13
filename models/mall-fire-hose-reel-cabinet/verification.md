# 434 verification · prepared local state

**Local asset/source: PASS. Overall integration: NEEDS REVIEW.** Physical Android/iOS: **NOT TESTED**. Final merged-base gate: **PENDING**.

## Base and scope

Prepared on exact local chain base `6d2819b971737a2777d791c73955c78aba203b96`, preserving prepared items 430–433. Canonical main was rechecked before gates and after them: `b7421d284b503ff923508fc3046b2193108f503a`, unchanged. GitHub PR #12 remains open, draft and unmerged, head `04d31c694520a0935a6c0e65b737bd91f43a8bc6`. No unmerged loader, app, UI or schema implementation was copied.

Only new item **V2.1 P0 434 Mall Fire Hose Reel Cabinet** is registered. No runtime door control, operating system, installation instruction, certification, pressure, flow or safety claim. Opaque metal door; no glass alpha claim.

## Executed local gates

| Gate | Result |
| --- | --- |
| Deterministic Blender 4.0.2 generation and real source reopen | PASS |
| Khronos glTF Validator | **0 errors / 0 warnings** |
| Actual metric bounds / independent module contract | PASS |
| 64 mesh parts: manifold edges / degenerate faces / positive signed volumes | PASS |
| 106 door angles, 21,624 conservative enclosure collision pairs | PASS, zero collisions |
| Minimum moving-door separation from enclosure/interior front plane | 0.017000 m |
| Coil: 449 cross-sections, 7 turns, measured pitch / interturn gap | 0.026999965 / 0.002999965 m |
| Isolated nozzle-tip geometry +20%, source door closed, saved/reopened/exported | PASS; 63 other mesh coordinate arrays unchanged; delivered source hash unchanged |
| Edited GLB validation | 0 errors / 0 warnings |
| Focused contracts | **6/6 PASS** |
| Full repository unit suite | **141/141 PASS** |
| Build and all 73 catalog GLBs | PASS |
| Library browser suite | **9/9 PASS** |
| One strict three-viewport pass | **FAIL 3/3**, preserved below |

The build retains its existing >500 kB JavaScript chunk warning. No unrelated code splitting or app change was attempted. Blender reports optional Draco unavailable; this GLB deliberately needs no compression decoder.

## Exact delivered artifact

- SHA-256: `78ee25359cb1783a505d62a6df98652cbad42135e13b14a929459e1a8f936cc5`
- 474,576 bytes; 15,156 triangles; 15,464 vertices; 64 independent mesh primitives; six opaque materials.
- Built `dist/assets/optimized-Bg0VWWrw.glb` is byte-for-byte equal to the delivered GLB.
- No textures, animations, cameras, lights or external buffers in the export.
- All six PNG masters and WebPs inspected: open hero, closed label, front, side, rear and interior. Framing corrected before final gate. Parent independently accepted open/closed studio and 390px initial browser appearance.

## One strict initial-base browser pass, not retried

Desktop Chromium **156.0.8078.4**, headless SwiftShader, viewport emulation only. Raw evidence: `reports/browser-initial-base/results.json`, PNGs and review sheets. **No error filtering, no retry-to-green, no loader patch.**

| Viewport | Functional observations | Unfiltered unexpected errors | Strict result |
| --- | --- | --- | --- |
| 1440 × 900 | Exact SHA/474,576 bytes, HTTP 200, drawing, orbit/zoom/reset/reopen/lifecycle/focus/overflow checks passed | 2 × `net::ERR_ABORTED` | FAIL |
| 768 × 1024 | Same functional checks passed | 1 × `net::ERR_ABORTED` | FAIL |
| 390 × 844 | Same functional checks passed | 3 × `net::ERR_ABORTED` | FAIL |

All three captured the exact consumed GLB, HTTP 200 responses and changing rendered pixels for orbit/zoom. Reset and reopen pixels exactly match the initial view; three repeated same-page cycles release drawing and restore card focus; there is no horizontal overflow. All 36 browser PNGs were inspected, including full-page/failure images. The failed assertions are the unfiltered old-loader request errors; this is **not** a green browser gate. No unexpected console/page exception was recorded.

Library results and run-time screenshots were copied from the test's default temporary artifact directory into `reports/library-initial-base/`; the repository's older evidence is untouched. Future isolated library runs should set `TEST_ARTIFACT_DIR`.

## Preservation and disposition

`reports/preservation.json` verifies all 72 old catalog assets and all old catalog collections unchanged, the old catalog byte prefix identical, and no modifications to old source/assets/evidence/app/UI/schema. The catalog now has 73 assets. Source pose is not runtime interactivity. Rights text is unchanged and downloads are false.

This is a **prepared local item**, not merged-base acceptance, not a release, and not hardware acceptance. No remote push, PR, merge, history rewrite or deployment was performed. Final merged-base integration is **PENDING / NEEDS REVIEW**.

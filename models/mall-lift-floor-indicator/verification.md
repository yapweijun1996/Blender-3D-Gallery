# 432 verification: local asset PASS; initial-base browser FAIL; overall NEEDS REVIEW

Date: 2026-11-12. This is prepared item 3/10 of the second batch, not a released model or completed merged-base integration.

## Base and scope

- Isolated local clone starts at `a77698b1116d18647977bb5865cdd8a552532ed0` (prepared 430 and 431), based on old main `b7421d284b503ff923508fc3046b2193108f503a`.
- Remote main was read with `git ls-remote` immediately before initial-base gates and was still `b7421d284b503ff923508fc3046b2193108f503a`. PR #12 was open, draft and unmerged. No unmerged first-batch commits were incorporated.
- Only item 432, its catalog registration, focused units, asset/browser checks and evidence were added. No application, viewer, loader, UI or schema changes. Existing `previewRotationY` only; no new preview fields.
- All 70 inherited catalog assets are unchanged. All 809 inherited model files except the append-only catalog are byte-identical. See `reports/preservation.json`.
- No remote push, PR action, merge or deployment. Final merged-base integration is **PENDING**. Actual Android/iOS hardware is **NOT TESTED**.

## Asset/source gates: PASS

| Check | Measured result |
| --- | --- |
| GLB | 43,292 bytes, SHA-256 `8b4ba00d43b990599d94772a6738467a191a1fb8ea9ea3cee462f271c9e48b31` |
| Geometry | 596 triangles; 1,104 vertices; 20 mesh primitives; five materials |
| Textures / animations | 0 / 0 |
| Khronos validator | 2.0.0-dev.3.10; 0 errors / 0 warnings |
| Size / axes | 0.42 × 0.16 × 0.0268 m; Blender +Z up / -Y front; glTF +Y up / +Z front |
| Mount / thickness | Back on wall plane; mount (0,0,0.08) Blender; housing 1.5 mm; bezel 3 mm |
| Component checks | Housing, open metal bezel, face, 14 independent digit segments, 3 independent arrow segments; correct 02 mapping |
| Source | Delivered Blender 4.0.2 source reopened; 20 editable meshes; metric units and unit scales |
| Real edit/re-export | 02/up → 03/down saved/reopened/exported; c/e segment materials change; arrow rotates; all mesh coordinate arrays and housing unchanged; new GLB Khronos 0/0 |
| Source protection | Original delivered .blend bytes unchanged after isolated edit proof |
| Previews | Five 768 × 768 PNG/WebP views; all WebPs below 150 KiB |
| Focused units | 5/5 PASS |

Evidence: `reports/assets.json`, `geometry.json`, `sources.json`, `source-edit.json`, `interface.json`, local metadata, and multiview previews. `status: validated` describes asset/source validation, not a full browser/mobile/release approval.

## Initial-base aggregate gates

- Full unit suite: **129/129 PASS**, `reports/unit.log`.
- Build and all catalog GLB validation: **PASS**, `reports/build.log`. Existing bundle-size advisory remains; no new package/scripts/lint/typecheck changes.
- Library browser suite: **9/9 PASS**, `reports/library.log`.
- Strict item browser run: **2/3 PASS, overall FAIL**, `reports/browser.log` and `reports/browser-initial-base/results.json`.

One fixed run in Desktop Chromium **156.0.8078.4**, Playwright cached revision 1248, SwiftShader. Viewport emulation only, not Android/iOS browsers.

| Viewport | Result | Unexpected request/console/page errors |
| --- | --- | --- |
| 1440 × 900 | PASS | 0 |
| 768 × 1024 | PASS | 0 |
| 390 × 844 | **FAIL** | One GLB `requestfailed`, `net::ERR_ABORTED` |

The failing URL is the actual served asset `/Blender-3D-Gallery/assets/optimized-B8YQTkCi.glb`. The old-base loader failure remains recorded. It was **not retried, filtered or patched**. A visually correct screenshot does not turn that case into PASS.

All three cases did independently complete exact consumed GLB bytes/SHA, HTTP 200 responses, real draw calls (100/140/140), orbit, zoom, exact initial/reset/reopen pixel equality, three additional close/open cycles, close-stop-rendering, restored card focus, hidden public download and no horizontal overflow before the final all-errors assertion. Full unmasked screenshots and pixel hashes are retained, including the 390 failure screenshot.

## Pixel review and limitations

The studio hero and five-view contact sheet were inspected, as were actual Gallery screenshots at 1440, 768 and 390 widths. The 02/up example is legible, frame and wall thickness visible, and the full asset is not clipped. The detail preview intentionally crops the outer frame to show segments. The parent independently accepted the hero and 390 initial view for this prepared asset.

This is static display appearance and source editability only. No live elevator state, runtime update, electrical interface, structural/load approval, fabrication guarantee or safety/code compliance is claimed. No change to rights or disabled public download. Final application integration must be checked on the eventual merged base, retaining this initial-base failure as historical evidence.

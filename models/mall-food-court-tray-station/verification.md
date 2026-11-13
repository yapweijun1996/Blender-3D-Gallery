# Verification · Mall Food Court Tray Station · 439

Prepared locally on inherited base **f96cf822fb43759adabcee8e57bb0c0ddffe02fa**. Exact V2.1 P0 item **439**, second-batch item **10/10**. This is current-base evidence only, not final merged-base acceptance or a release. No push, PR, merge, history rewrite or deployment performed.

## Asset and editable source

- Final optimized GLB SHA-256: **6dbf9a5ae6260f4473a4e16e600e9557f08de087707a0b38209922014d0ad585**.
- **353,656 bytes; 5,412 triangles; 12,903 vertices; 15 primitives; 13 independent semantic modules; 8 materials; no textures, animations or external buffers.**
- Khronos Validator 2.0.0-dev.3.10: **0 errors / 0 warnings**.
- Measured overall **1.50 W × 0.66 D × 1.49 H m**, floor origin. Counter top is 0.95 m. Counter underside meets the cabinet sides; there is no unsupported visual gap.
- Live GLB ray tests enter both true shelf openings and hit the back panel, not a false black aperture. Opening width 1.36 m; clear bay height 0.33 m above each shelf.
- Four independently editable 0.45 × 0.33 × 0.03 m trays. Downward rays hit each real 6 mm bowl floor below its lip. Lower stack has 5 mm separation. Upper tray has 3 mm shelf clearance and passes a swept-box removal test 0.62 m forward without fixed-module collision, ending completely outside the counter footprint.
- Blender 4.0.2 delivered source reopened successfully: metric units, unit scales, no external image dependencies, two editable FONT labels. All evaluated exported source parts have closed manifold topology, positive volume and no degenerate faces; sign lettering fits the header.
- Real source edit proof: counter mesh vertices widened 4%, only Tray04 material recoloured, and TRAY RETURN changed to RETURN TRAYS. Saved copy reopened and re-exported without regeneration. Exactly Counter, SignText and Tray04 changed; ten other modules and all transforms stayed identical. Shipped source hash unchanged. Edited GLB also Khronos 0/0.
- A development inspection caught a touching bundled Bfont A contour. A 0.05 mm FONT outline offset resolves it without weakening manifold assertions. An early source-edit lookup found a renamed source object; source names and collection-based lookup were corrected. Both original failures remain in the reports directory.
- Six 768 px PNG masters and WebPs: hero, front, rear, side, interior and source-only tray-removal pose. The interior is an intentional shelf-detail crop. WebPs range from 7,918 to 19,148 bytes.
- All six studio views, all **34** strict-browser captures and all **16** library captures were inspected. Readable original sign, visible shelf openings and tray bowls, no model clipping or missing geometry. Full 390 px page inspected separately. The parent independently accepted hero/removal and 390 px initial pixels before local commit.

## Current-base gates

- Focused source/geometry/scale/budget contracts: **7/7 PASS**.
- Full unit suite: **172/172 PASS**, no failures or skips.
- Production build and catalog GLB validation: **PASS**. Existing shared-chunk size warning remains.
- Library browser suite: **9/9 PASS**.
- Strict viewer: **exactly one fixed three-viewport pass**, desktop Chromium 156.0.8078.4 / SwiftShader on shared Ubuntu, not native mobile:
  - **1440 × 900: FAIL**, one unfiltered GET GLB `net::ERR_ABORTED`.
  - **768 × 1024: PASS**, no unexpected request/console/page errors.
  - **390 × 844: PASS**, no unexpected request/console/page errors.
- All three cases verified exact consumed GLB SHA and byte length, all five GLB HTTP responses at 200, real drawing, orbit and zoom, pixel-exact reset/reopen, three repeated lifecycle cycles, stopped rendering on close, restored card focus, disabled download and no horizontal overflow.
- The 1440 px existing-loader failure remains a failure. No retries to green, filtering, duplicate loader fix, unmerged first-batch implementation copy, app/UI/schema or new preview-camera/light fields were introduced.
- Raw library results retain their historical harness environment wording; the actual run was shared Ubuntu with desktop Chromium viewport emulation.

## Preservation and unresolved gates

Main rechecked before gates and at final review: **b7421d284b503ff923508fc3046b2193108f503a**. PR 12 remains open/unmerged, head **04d31c694520a0935a6c0e65b737bd91f43a8bc6**.

**All 1,800 previous non-catalog tracked files are byte-identical** to the inherited base, including assets and evidence for prepared items 430–438. All old catalog collection content, order, rights and metadata are unchanged; only one collection was appended. Catalog count rises from 77 to 78, not by four extra tray types. Public downloads remain false.

**Final merged-base integration and second-batch quality gate: PENDING. Physical Android/iOS: NOT TESTED.** This is an illustrative tray-return prop, not a waste-sorting station, coffee counter, hygiene/safety-certified product, fabrication specification or functional automation. Tray-removal imagery is a geometric source pose, not runtime UI.

Evidence: `reports/assets.json`, `geometry.json`, `sources.json`, `source-edit.json`, `preservation.json`, `gate-exitcodes.json`, unit/build logs, `browser/results.json`, `library/results.json`, contact sheets and upstream snapshots. Initial failed logs and initial export metrics are retained explicitly, not substituted for the final exact-byte evidence.

## Diff review

Authored source, tests, metadata and documentation pass whitespace checking. The one whole-diff warning is raw `reports/build.log:273`, where Vite emitted trailing whitespace after `[plugin builtin:vite-reporter]`. That raw evidence line is deliberately preserved unchanged. Staged changes are limited to this asset, its two test files and its single catalog append.

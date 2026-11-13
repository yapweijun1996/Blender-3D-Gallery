# Mall floor tile verification · 2026-11-12

**Overall NEEDS REVIEW: actual Android and iOS browsers are untested. Local desktop acceptance passed. No push, PR, publication or deployment performed.**

This is selected backlog V2.1 item 421, one logical kit in the ten-model batch. Base is the prior railing commit `a1003a9`, itself based on `b7421d2`. Existing model files, app code and tests are preserved; only a new collection is inserted before service desk, leaving sign-to-queue adjacency unchanged.

## Final authored asset, before loader integration

- GLB: **155,964 bytes; 604 triangles; 1,064 vertices; 9 primitives; 3 materials; one 512 × 512 original embedded PNG; no animations**.
- SHA-256: `328a091a1372b0246694484d0cea05319bad032cfa603ed030b69ef87153c305`.
- Measured GLB X/Y/Z: **1.200000048 / 0.029999999 / 1.200000048 m**, minimum Y = 0.
- Blender 4.0.2 ARM64 source reopening: **PASS**. Five independently editable, closed manifold mesh parts with positive volume and a packed original texture. Source hash in `reports/sources.json`.
- Isolated saved-source edit/re-export: **PASS**. First slab's top vertices raised 4 mm; shared finish roughness changed 0.32 → 0.48. Other slab and bed bounds and embedded texture remain unchanged; shipped source remains unchanged. Edited export also has zero validator errors/warnings. See `reports/source-edit.json`.
- Khronos validator 2.0.0-dev.3.10: **0 errors, 0 warnings**. Self-contained buffers/image, no camera/light/animation. See `reports/assets.json`.
- Actual exported triangle raycasts: slab wearing surface 30 mm, grout surface 29 mm. Six sample locations pass.
- Actual exported 3 × 3 repeat and alternating quarter-turn layouts: **PASS**, 36 tiles and 60 measured 4 mm joints per layout. Maximum joint error 3.96e-8 m and maximum module AABB boundary error 4.77e-8 m, both floating-point scale. No overlap above 1e-6 m. See `reports/assembly.json`.
- `npm test`: **123/123 PASS**, including four added floor-tile tests. No old tests altered or weakened.
- `npm run build`: **PASS**, including catalog GLB validation. Existing large-JavaScript-chunk warning remains.
- `node scripts/test-mall-floor-tile.mjs`: **3/3 PASS** at 1440×900, 768×1024 and 390×844. Exact final GLB bytes/SHA consumed, HTTP 200, real WebGL draw calls, orbit/zoom/reset pixel changes, disabled downloads and no horizontal overflow. No console, page or request failure. No `requestfailed` or `ERR_ABORTED` filtering or retry-to-green.
- `npm run test:library`: **9/9 PASS**. The final run uses a dedicated artifact directory.

Toolchain: Node 22.23.3, Three.js 0.187.0, Playwright 1.64.1 and Ubuntu ARM64 desktop Chromium with software WebGL. Exact Chromium version is in `reports/browser.json`. Resizing a desktop browser is not Android/iOS testing. No real touch-hardware, mobile performance or mobile certification claim is made.

## Visual review and geometry correction

Actual pixels were inspected for final perspective, top and edge views, the 3 × 3 imported-GLB assembly, and all three initial gallery viewports. Warm ivory aggregate, narrow continuous grout lines, eased edges and slab thickness are visible without obvious clipping, missing texture, duplicate borders or holes. The existing gallery initial elevated view shows the top surface. Screenshots and contact sheets are in `reports/screenshots/`. Previews are imported from the real exported GLB, not replacement render geometry.

The first draft had its grout surface at the support height, 18 mm below the slabs. Although that draft passed 123 tests, build, 3 strict browser cases and 9 library cases, the grout recess was corrected to 1 mm. The final closed grout mesh fills joints without overlapping a solid full-height box through the slabs. Geometry, source edit, renders and all acceptance checks were rerun because the artifact changed. The first draft's reports and logs remain under `reports/initial-pass/`; they are not evidence for the final SHA.

Gallery WebP previews are about 13–15 KB each. Lossless archival render PNGs are about 814–845 KB, above the proposed 300 KiB poster target; those archival PNGs are not the gallery thumbnail payloads. There are no external texture rights to resolve. Public redistribution terms remain unspecified and public downloads remain disabled.

The prior glass-railing 8/9 strict browser failure is unchanged in its original reports. This floor asset's passing cases do not establish that the unrelated intermittent loader failure was repaired.

Committed text-log copies normalize trailing whitespace only; raw command logs remain in the isolated workspace. No diagnostic lines or failures were removed.

## Combined loader integration

After committing the floor asset as `4ff7771`, the separately reviewed loader fix `1a049ab` was fetched from the local diagnostic checkout and cherry-picked as `ea397d2`. No remote fetch, push, PR, merge or deployment was performed. The combined runtime tested at `ea397d2144f7fd50528461774d26a65b7b476231` passed:

- Unit tests: **123/123**; build/asset validation: **PASS**.
- Unchanged strict floor harness: **3/3**; unchanged strict glass harness: **9/9**. Every request/console/page-error array is empty and consumed GLB hashes match.
- New loading lifecycle regression: **4/4**, covering a real partial-transfer cancellation followed by reopen, HTTP 503 retry, truncated GLB retry and injected transport failure retry. Intentional fault events are explicitly matched; no unexpected error is hidden.
- General library suite: **9/9**.

Separate evidence, command logs, exact source identity and all twelve initial asset screenshots are under `reports/integration/`. All existing authored assets, the catalog and the floor harness remain unchanged from the asset commit. Original railing 8/9 results and the floor's pre-fix checks are preserved; this new result does not rewrite historical failures. A second reviewer independently inspected the four-angle floor contact sheet and integrated narrow-viewport floor rendering. Physical Android/iOS remains **NEEDS REVIEW**.

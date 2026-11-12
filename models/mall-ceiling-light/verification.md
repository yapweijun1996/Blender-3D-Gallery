# Mall Ceiling Light verification, 2026-11-12

## Result

**Overall: NEEDS REVIEW.** Artifact, source-edit, assembly and desktop technical checks pass. The correctly oriented fixture initially shows its rear under the existing elevated gallery camera. Orbit exposes a bright static emissive diffuser; the surrounding frame is still dark under upper-biased gallery lighting. These presentation limits are not disguised as full visual approval.

**Physical Android/iOS: NOT TESTED.** Narrow desktop viewports do not establish mobile GPU, native browser, touch or performance support. This commit makes no viewer or metadata-schema changes; separately approved per-asset preview configuration is outside its scope. No remote push, PR, merge, release or deployment.

## Measured asset

- GLB: 125,008 bytes, 1,900 triangles, 3,624 vertices, 11 mesh primitives, four editable materials.
- No textures, external URLs, cameras, lights, animations or decoder dependencies.
- GLB bounds: 0.576 × 0.065 × 0.576 m, glTF X/Y/Z. Bezel underside Y=0; fastener heads extend to Y=-0.001; rear driver top Y=0.064.
- GLB SHA-256: `b8b0b31c7657028dff44f8c04ba7e65b07feac892b4849b81bb0a1fd78432cf8`.
- Source SHA-256: `881ff73ec593c8c96bc19e3eebf0a7f4f085fe43655304cd0788abdf977e68bd`.
- Five served WebP previews (128-sample actual-GLB renders): 2,898–8,600 bytes. Full-resolution PNGs are archival render evidence, not gallery card images.
- Source metres +Z up; GLB metres +Y up. Diffuser faces down, not inverted for the starting camera.

## Executed checks

| Check | Result | Evidence |
| --- | --- | --- |
| Khronos glTF Validator 2.0.0-dev.3.10 | PASS, 0 errors / 0 warnings | reports/assets.json |
| Metres, bounds, budgets, named parts, diffuser/frame/fastener surface rays | PASS | validate.mjs, reports/assets.json |
| Source reopen, 11 positive-volume closed manifold mesh components | PASS | inspect_sources.py, reports/sources.json |
| Actual saved-source mesh/emission edit and re-export | PASS | reports/source-edit.json |
| Mount into each actual 422 bay, default and quarter-turn | PASS, 8/8 layouts | reports/assembly.json |
| Full Node unit suite | PASS, 131/131 | reports/unit-final.log |
| Production asset validation + Vite build | PASS | reports/build-final.log |
| Strict Chromium direct viewer, 1440×900 / 768×1024 / 390×844 | PASS, 3/3 | reports/browser.json |
| Library regression suite | PASS, 9/9 groups | reports/library.json |
| Actual-GLB studio multiangle pixel inspection | PASS | previews/*.png and *.webp |
| Gallery initial side / underside frame lighting | NEEDS REVIEW | reports/browser/*-initial.png, *-underside.png |
| Physical Android / iOS | NOT TESTED | No device evidence |

### Assembly and edit proof

The geometry assembly validator loads both shipped GLBs, removes only the selected PANEL_1..4 child, then places the fixture at that bay centre with Y=0.008 m above the ceiling root. In all eight cases it preserves the other three panels, nine rails and twelve suspension meshes with identical transforms. Fixture footprint matches the removed panel; it does not overlap retained component AABBs. Actual ray intersections confirm the diffuser is visible at Y=0.011 and the three untouched panel undersides remain at Y=0.008. These are visualization assembly checks, not mechanical installation certification.

The source-edit test reopens the shipped .blend, saves an isolated copy after lowering only the diffuser underside vertices by 1 mm and changing emission RGB (0.8,0.73,0.55) to (0.3,0.25,0.18), and invokes --export-source. The edited GLB validates 0/0; all other mesh bounds and the shipped source/export remain unchanged. Edited SHA-256: `34351aabbef4f18c7a53eb6cf518ed72e6743e0aee382570dfc488e3b76b1eb5`.

### Strict browser coverage

Desktop Chromium 156.0.8078.4, Linux ARM64, Node 22.23.3, headless SwiftShader. Each viewport checks actual consumed GLB bytes and exact SHA, HTTP 200, positive draw calls, title, disabled download, orbit, zoom, reset, underside orbit and absence of horizontal overflow. All requestfailed, console errors, page errors and HTTP errors are collected; **no ERR_ABORTED filtering**. All three final cases have empty error arrays.

The unchanged library harness retains an inherited hardcoded macOS headless label. The actual execution environment is Linux ARM64, captured in reports/environment.json. That label is not macOS evidence.

### Pixel observations

The actual-export studio renders show a recessed square opal face inside an ivory frame, four small visible front fasteners, annular housing thickness and a rear driver cover with cable entries. Assembly preview shows one lit-style cassette and three retained mineral-fibre-style panels with the grid and hangers intact. No obvious clipped bounds, detached visible pieces or z-fighting were observed.

The inspected 1440 and 390 initial gallery screenshots fit the fixture without cropping but show its rear. Their underside screenshots show a warm bright diffuser with dark frame. Emission is appearance only in Three.js: no dynamic light source, switch, bloom or lighting-performance claim.

### Failures, correction and warnings

An initial preparation run stopped on a missing source-inspection script; the missing file was confirmed, written and the full generation/inspection pipeline rerun successfully. Initial units passed 129/131 because the new collection had been placed first, breaking two legacy registry fixtures. The collection was appended instead, restoring original order; **no existing tests were edited or weakened**. The failed unit log and initial browser/library results are retained; captured text logs have trailing whitespace normalized only. Final all-suite rerun passes.

Initial library output used its default temporary directory due an incorrect environment-variable name; the final run uses the harness's actual TEST_ARTIFACT_DIR in the isolated workspace. The existing Vite shared-chunk warning remains. Blender logs optional Draco support unavailable; no Draco compression is requested or needed.

## Preservation and rights

One selected logical model, V2.1 P0 item 423, batch item 4/10. All existing catalog entries and order, models, sources and test evidence remain unchanged. Catalog modification is a single appended collection. No app, schema, existing test or unrelated code changes. Original geometry and materials; no third-party artwork, fonts or models. Owner-project reuse authorized; public redistribution terms unspecified, public download false.

# Mall Structural Column verification

Local source, geometry, placement, studio and Gallery visual gates **PASS**. Overall **NEEDS REVIEW** because physical Android and iOS are **NOT TESTED**. Visual architecture only: no structural load, safety, engineering, building-code or installation certification; no runtime interaction, deployment or release.

## Deliverable

- Selected V2.1 P0 item 427; batch item 8/10, one logical model.
- 78,744-byte optimized embedded GLB; 1,404 triangles, 2,808 vertices, 13 independent mesh primitives and 3 named materials. No textures, animations, lights, external references or decoder.
- Bounds 0.60 × 3.00 × 0.60 m (glTF X/Y/Z). Bottom Y=0; source Blender +Z maps to glTF +Y.
- SHA-256: `5a856c9a4e30b7cbde2e99cb50e4e43e9f45a86dd3e504f4dea4708cbe8874aa`.
- Five 768 × 768 studio PNGs and WebPs: oblique, front, rear, actual single-column placement and two-column assembly. WebPs 6,096–34,190 bytes; PNGs are archival render evidence.
- The square shaft has 8 independently editable ivory panels around a core, a charcoal plinth, two shadow reveals and an ivory cap. Generator dimensions and source mesh/modifier/material editing are retained.

## Gates and evidence

| Gate | Result | Evidence |
| --- | --- | --- |
| Khronos GLB validator | PASS, 0 errors / 0 warnings | reports/assets.json |
| Live root, dimensions, geometry, materials, budgets | PASS | validate.mjs |
| Internal column mesh pairs | PASS, 78 comparisons, no penetration | reports/assets.json |
| Actual floor / ceiling placement | PASS, 2 layouts, 20,345 column/context mesh-pair checks | reports/assemblies.json |
| Blender source reopen, manifold positive-volume meshes | PASS, 13/13 | reports/sources.json |
| Actual source edit, save and re-export | PASS, edited GLB 0/0 | reports/source-edit.json |
| Full Node unit suite | PASS, 154/154 | reports/unit-final.log |
| Catalog validation and production build | PASS | reports/build-final.log |
| Strict Gallery 1440×900 / 768×1024 / 390×844 | PASS, 3/3 | reports/browser/results.json |
| Library regression | PASS, 9/9 groups | reports/library/results.json |
| Five studio and three Gallery initial images | PASS, actual pixels inspected | previews/ and reports/browser/ |
| Physical Android / iOS | NOT TESTED | No native-device evidence |
| Existing source / assets / evidence / catalog | PASS | reports/preservation.json |

## Placement and edit proof

The layouts clone the actual exported column and existing floor/ceiling GLBs. The floor modules sit at Y=-0.03 so their finished tops touch the column bottom at Y=0 without volume penetration. The ceiling underside is Y=3.0. One full 1.2 m ceiling module is omitted above each column, giving 0.30 m horizontal clearance from the 0.60 m cap to the neighbouring grid. This intentionally reserved opening is a scene-layout convention, not a construction closure or structural connection. The two-column layout uses 3.60 m centre spacing and 3.00 m plinth-edge clearance.

The validation reads every actual mesh bound after world transforms. All 20,345 column/context mesh pairs are checked for volume penetration with a 1e-6 m floating-point tolerance. Context source hashes are recorded; prior floor/ceiling bytes are unchanged. Square axis-aligned placements make AABB comparisons appropriate here.

The source reopens with 13 positive-volume manifold editable objects and 3 named materials. An isolated copy narrows only CLADDING_Front_Lower from 0.50 to 0.48 m and changes the shared ivory finish roughness from 0.58 to 0.72. Saving and re-exporting changes the expected mesh/material; the other 12 mesh position arrays and bounds, other materials and shipped source hash remain unchanged. The edited GLB validates 0/0. Shared ivory roughness affects all parts using that material, as expected.

Five focused contracts run under npm test and include live GLB geometry/placement validation, metadata/hash/source checks, PNG/WebP signatures and budgets, rights and static-scope assertions.

## Browser and visual review

Chromium 156.0.8078.4 on Linux ARM64 with headless SwiftShader. This is desktop Chromium viewport emulation, not Android/iOS execution. Node v22.23.3; Blender 4.0.2. The inherited library harness has a macOS wording label; reports/environment.json identifies the actual runtime.

Each strict case checks exact consumed GLB SHA and byte count, HTTP 200, positive WebGL draws, title, hidden download, orbit, zoom, exact-pixel reset, additional orbit, close/exact reopen and no horizontal overflow. All requestfailed, console errors, page errors and HTTP errors are retained and asserted absent; there is no error filtering.

The oblique, front, rear, placement and assembly studio images show the real imported GLBs. All five studio WebPs and all three Gallery initial PNGs were inspected: the simple square column, separate base/cap, midpoint cladding seam and full model framing are clear. Placement views show the reserved ceiling bays and coherent ivory/charcoal palette.

Independent parent review also inspected the mobile Gallery initial image and both corrected placement renders, accepting local visual quality while retaining the non-engineering placement limitation.

## Corrections and limitations

Pixel inspection caught coplanar studio-backdrop interference with the real floor tiles in the initial two context renders. Only the non-exported studio floor was lowered below the floor modules; the front-view camera was raised slightly to remove a backdrop-edge artifact. Three views were re-rendered and inspected. Source, shipped GLB and tested placement geometry were unchanged. Original render log and corrective render log are retained.

The inherited Vite >500 kB chunk warning remains. Build-log trailing whitespace was normalized for diff hygiene; all messages and warnings remain. Blender notes optional Draco unavailable; this asset does not request Draco. Render grain is confined to Cycles evidence images, not GLB geometry. No app, schema or UI changes; only the existing approved preview camera metadata is used.

Catalog grows from 77 to 78 models, preserving all earlier entries/order and prefix bytes. Every other pre-existing tracked file is unchanged. Original asset; owner-project reuse authorized, public redistribution unspecified and download disabled. Local commit only: no push, PR, merge or deployment.

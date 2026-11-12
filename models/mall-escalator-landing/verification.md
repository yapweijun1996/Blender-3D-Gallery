# Verification: Mall Escalator Landing 429

Local geometry, source, floor connections, studio and browser visual checks: **PASS**. Overall: **NEEDS REVIEW** because physical Android/iOS testing remains **NOT TESTED**. No deployment or release performed.

## Verified artifact

- V2.1 P0 item 429 only, not a full/moving escalator.
- GLB SHA-256: aa2632a479f3e474b38413667f01c308d0a542325e451660f0e67be5384bc63d.
- 83,352 bytes; 1,616 triangles; 2,616 vertices; eight independent mesh primitives; five materials.
- Blender source: eight closed manifold meshes with positive volume, metre scale, origin at underside centre.
- GLB extents 1.2 × 0.03 × 1.2 m; correct Blender Z-up to glTF Y-up conversion and all five connector anchors.
- Khronos glTF Validator 2.0.0-dev.3.10: **0 errors, 0 warnings**.
- No textures, animation clips, external URLs, cameras/lights, or decoder requirement.
- Five 768×768 PNG masters and WebP previews. WebPs are 8.2–23 kB, all below 150 KiB.
- Public download remains disabled; no new public redistribution license assumed.

## Actual geometry, not metadata assertions

The live GLB validator checks the 25 rib pairs on each separate plate, 27 comb fingers, plate seam and comb elevation from actual vertex positions. Three tests load the unchanged existing 421 GLB at front/left/right placements. Each tests 72 independent-mesh AABB pairs for volumetric overlap and raycasts four pairs of actual wearing surfaces. All joints align within 1 µm, with no positive-volume intersection; both wearing surfaces are 30 mm high. Original 421 boundary grout remains 1 mm recessed and is measured separately.

Only the floor connections are verified. Future escalator 430 does not exist in this contribution. Its documented connector envelope is **provisional / NOT TESTED**, not evidence of mechanical compatibility or code/safety/manufacturer certification.

## Blender source editing

The delivered .blend was reopened. An isolated copy lowered only the front plate ribs from 30 to 29 mm and changed shared plate-material roughness 0.34→0.50. Its self-contained copied generator reexported every component without sibling files. The other seven mesh geometries and other materials were unchanged; edited GLB also validates 0/0. The shipped source hash was verified unchanged. See reports/sources.json and reports/source-edit.json.

## Commands and results

- Source generation/render/import inspection: PASS, Blender 4.0.2 on Ubuntu ARM64.
- Live Khronos/geometry/assembly validation: PASS.
- Focused contracts included in npm test: five tests.
- npm test: **165/165 PASS**, no skipped/cancelled tests.
- npm run build: PASS, including catalog/GLB validation. Existing >500 kB shared-chunk warning remains; it is not a landing GLB warning.
- scripts/test-mall-escalator-landing.mjs: **3/3 PASS**, 1440×900, 768×1024, 390×844.
- npm run test:library: **9/9 PASS**.
- Existing tracked files byte-preserved except append-only catalog registration; old catalog entries/order unchanged. See reports/preservation.json.
- No app code, UI, schema, package dependencies or prior model/evidence files changed.

## Browser and visual evidence

The strict asset browser harness confirms the SHA of bytes actually consumed by the viewer, 83,352 bytes, HTTP 200, nonzero WebGL draw calls, keyboard orbit, zoom, exact reset pixels, additional orbit, close and exact reopen pixels, and no horizontal overflow. Console/page/request/HTTP errors must be empty; **no requestfailed/ERR_ABORTED filtering** is applied.

Final studio hero, top, interface, underside and actual-floor assembly images were inspected. An initial interface crop was corrected by changing only camera framing. Generic browser lighting made the ribs too subdued; existing per-asset previewLighting fields improve contrast without altering the GLB/materials or application. Final browser screenshots were inspected at all three widths, including all reset/reopen/orbit states and page views.

Runtime is **desktop Chromium 156.0.8078.4 / Playwright 1.64.1 with SwiftShader on Ubuntu ARM64**, not Android/iOS hardware. Existing library harness hardcodes “macOS headless” in its report; reports/runtime.json corrects that environmental label while preserving its raw report. Viewport emulation is not physical-device coverage.

No mechanical functionality, escalator movement, certified anti-slip performance, installation engineering, fabrication accuracy, safety standard or building-code compliance is asserted. This is a static reusable visual architecture asset.

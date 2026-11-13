# Mall Glass Partition verification

Local artifact/source/visual gates **PASS**. Overall **NEEDS REVIEW** because actual Android and iOS devices are **NOT TESTED**. No runtime interaction, structural or safety approval, deployment or release is claimed.

## Measured deliverable

- Item 426, selected V2.1 P0, batch item 7/10, one logical asset.
- 54,420-byte optimized GLB, 852 triangles, 1,704 vertices, 15 editable mesh primitives, 3 named materials, no textures/animations/lights/decoder.
- Bounds 1.20 × 2.40 × 0.06 m; ground minimum glTF Y=0. Post-centre pitch 1.14 m.
- GLB SHA-256: `115d1e7a4c66d0ac5af08af51627f5d1a04c037156f9c2178b815ce4857ffd7f`.
- Source SHA is in reports/sources.json. Shipped source remains unchanged after independent editing proof.
- Five 768 × 768 PNGs and corresponding WebPs: oblique, front, rear, three-bay straight and three-bay corner. WebPs 10,472–27,122 bytes.

## Executed checks

| Check | Result | Evidence |
| --- | --- | --- |
| Khronos glTF Validator | PASS, 0 errors / 0 warnings | reports/assets.json |
| Root, scale, bounds, materials, no external references, budgets | PASS | validate.mjs |
| Actual GLB straight and both corner-direction assemblies | PASS, 3 cases / 2,212 mesh-pair checks | reports/assemblies.json |
| Source reopen and positive-volume closed manifold parts | PASS, 15/15 | reports/sources.json |
| Real independent mesh/material source edit, save, re-export | PASS, edited GLB 0/0 | reports/source-edit.json |
| Full Node unit suite | PASS, 149/149 | reports/unit-final.log |
| Catalog validation and production Vite build | PASS | reports/build-final.log |
| Strict gallery 1440×900 / 768×1024 / 390×844 | PASS, 3/3 | reports/browser/results.json |
| Transparent / opaque / hidden checker controls | PASS | reports/glass/results.json |
| Existing library regression | PASS, 9/9 groups | reports/library/results.json |
| Original studio and browser pixels | PASS local visual review | previews/ and reports/browser/ |
| Physical Android / iOS | NOT TESTED | No native-device evidence |
| Prior assets, sources, evidence and catalog preservation | PASS | reports/preservation.json |

## Assembly and editability

Tests clone the real shipped GLB, physically remove each incoming POST_Left, and align its named connector with the prior right connector. The straight three-bay and three-bay corner have four shared/end posts and 43 meshes; the opposite two-bay corner has three posts and 29 meshes. Maximum connector error is 1.44e−8 m. All mesh pairs are tested with axis-aligned bounds, appropriate to these 0°/±90° arrangements, with 1e−6 m floating-point tolerance. Contacts at track/post, glass/frame and mullion/transom interfaces are permitted; no volume penetration or duplicated posts is accepted. These are layout tests, not structural connection certification.

The saved Blender source independently reopens with 15 editable positive-volume manifold meshes. An isolated copy raises only BAND_Left_Front top vertices 10 mm and changes frame roughness from 0.32 to 0.5. Saving and exporting that copy changes the expected geometry/material while preserving all other mesh bounds and the shipped source hash. Both original and edited GLBs validate 0/0. The gallery does not expose edit or assembly controls.

Four focused unit contracts rerun the live GLB validator and assembly checks under npm test, then validate metadata metrics, source hash and edit evidence, preview image signatures/budgets, static scope and disabled-download rights.

## Browser and visual evidence

Chromium 156.0.8078.4, Linux ARM64, headless SwiftShader. Each viewport asserts the consumed GLB byte count and SHA match the shipped file, HTTP 200 GLB responses, positive WebGL draw calls, correct title, hidden download, orbit, zoom, exact-pixel reset, additional orbit, close/exact reopen and no horizontal overflow. Every requestfailed, console error, page error and HTTP error is retained and asserted absent. No ERR_ABORTED filtering.

The checker-target diagnostic loads the unchanged GLB and verifies status/SHA. Original alpha glass preserves the checker pattern with a visible aqua tint; opaque control completely obscures it; hidden control reveals the untinted target. All three actual images were inspected. The unchanged library harness has an inherited macOS label; reports/environment.json records the actual Linux runtime. Viewport emulation is not Android/iOS testing.

Independent visual review additionally inspected the tablet page, corner assembly and original checker image, confirming proportions, shared corner post, framing and transparency.

Studio images show the real imported GLB, including actual shared-post assemblies. No substitute geometry or painted-over output is used. Light grain in the Cycles studio renders does not affect the delivered browser GLB.

## Corrections, warnings and scope

The first Blender invocation omitted background mode and exited before creating assets because no X11 display was available. It was corrected to --background; the initial log is retained as generation-display-failed.log. Geometry/source/build/browser gates subsequently passed without weakening assertions.

The inherited Vite chunk-size warning remains. Blender reports optional Draco unavailable; this export does not request Draco. No unrelated refinements or app/UI/schema changes were made. Only the existing approved preview camera setting is used.

Prior catalog prefix bytes, entries and order are preserved; the new collection/asset raises the catalog from 76 to 77 models. All other pre-existing tracked files are unchanged. Original geometry/materials, owner-project reuse authorized, public redistribution unspecified, download false. Local commit only; no push, PR, merge or deployment.

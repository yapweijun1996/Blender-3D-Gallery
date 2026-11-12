# Mall Shopfront Door verification, 2026-11-12

## Result

**Local asset visual approval: PASS.** Actual-export closed/front/rear/open studio renders and the initial desktop gallery view were inspected. The glazed double door, frame, pull hardware and frosted visibility bands are recognizable. Both open-preview leaves actually swing clear of the frame. No clipped model bounds, unintended detached large parts or visible z-fighting were observed. The glass diagnostic visibly distinguishes original transparent, opaque and hidden controls.

**Overall: NEEDS REVIEW only for unverified target-device coverage. Physical Android/iOS: NOT TESTED.** Desktop viewport emulation is not native browser, mobile GPU, touch or performance evidence. This is a static gallery asset with editable source/GLB hinge roots, not runtime click-to-open functionality.

## Measured asset

- GLB 145,752 bytes, 2,604 triangles, 5,016 vertices, 33 mesh primitives, 4 materials.
- No textures, external resources, animation clips, exported cameras/lights or decoder dependency.
- Overall 2.10 × 2.40 × 0.183 m (glTF X/Y/Z), minimum Y=0. Origin is floor midpoint.
- Fixed aperture 1.94 × 2.32 m; paired 90° open clearance including pull hardware: 1.734000 m.
- GLB SHA-256: daf0d6aa4347a58c9b39f2b3e32f0a24e6d66b041a8669c6c1b225343864c402.
- Source SHA-256: a3d6f53c62459712e27fcc8f42928fde17f4ced823ae0c4310d287d6a98548a4.
- Four 768 × 768 PNG renders and WebP previews. Served WebPs are 15,516–42,302 bytes; PNGs are archival render evidence.

## Executed gates

| Gate | Result | Evidence |
| --- | --- | --- |
| Khronos glTF Validator 2.0.0-dev.3.10 | PASS: 0 errors / 0 warnings | reports/assets.json |
| Metres, bounds, origin, component hierarchy, budgets and alpha | PASS | validate.mjs |
| Independent/paired hinge motion and frame/leaf collision separation | PASS: 21/21 cases | reports/articulation.json |
| Source reopened, positive-volume closed manifold meshes | PASS: 33/33 | reports/sources.json |
| Real source mesh/material edit, saved then re-exported | PASS: edited GLB also 0/0 | reports/source-edit.json |
| Full Node unit suite | PASS: 141/141 | reports/unit-final.log |
| Catalog asset validation + production Vite build | PASS | reports/build-final.log |
| Strict gallery 1440×900 / 768×1024 / 390×844 | PASS: 3/3 | reports/browser/results.json |
| Glass transparency diagnostic | PASS | reports/glass/results.json |
| Existing library regression suite | PASS: 9/9 groups | reports/library/results.json |
| Actual-export studio and gallery pixel inspection | PASS | previews/ and reports/browser/ |
| Physical Android / iOS | NOT TESTED | No physical device evidence |

## Articulation and source edit

The validator loads the shipped GLB and exercises left-only, right-only and both hinge roots at 0, 15, 30, 45, 60, 75 and 90 degrees. All fixed-frame world matrices and leaf-child local transforms remain unchanged. Each leaf assembly clears stationary jamb/header geometry, using conservative per-part AABB separation, and clears the opposite leaf. Coaxial bearing interfaces and within-leaf hardware attachments are intentional contacts, not treated as collisions. After reset, original root-child transforms are restored exactly. Source tests independently rotate both saved-source hinges and confirm corresponding glass movement without frame movement.

The edit proof reopens the shipped .blend, raises only HANDLE_Left_Front top vertices 20 mm, changes hardware roughness from 0.3 to 0.55, saves an isolated copy and exports with --export-source. All other mesh bounds and the shipped .blend remain unchanged. The edited GLB hash differs and validates 0/0.

## Browser and glass evidence

Desktop Chromium 156.0.8078.4 on Linux ARM64, headless SwiftShader, Node 22.23.3. Exact response/consumed GLB bytes and SHA match the file above; every GLB response is HTTP 200. All three viewport cases record positive WebGL draws, correct title, disabled download, orbit, zoom, exact reset, extra orbit, close and exact reopen, and no horizontal overflow. Requestfailed, console errors, page errors and HTTP errors are all collected with no ERR_ABORTED filtering; final arrays are empty.

The glass diagnostic loads the identical shipped GLB and places a checker target behind it. Original opacity 0.22, opaque opacity 1, and hidden-glass controls produce three different image hashes. Pixel review confirms the target is visible through original glass and obscured by opaque glass. This verifies alpha blending, not physical refraction.

The unchanged library harness has an inherited macOS label. The actual test environment is Linux ARM64, recorded in reports/environment.json. That label is not evidence of macOS or native mobile testing.

## Corrections and warnings

Initial validation exposed an exact duplicate material definition emitted by Blender for the same stainless hardware. Export now deduplicates only exactly equal material JSON objects and remaps primitive material indices; geometry, BIN data, nodes and pivots are preserved. Initial failed validation evidence remains in reports/validate-initial-failed.log. A UV-cleanup attempt used an unsupported Blender API and failed before generating output; it was removed, not hidden by reducing validation (reports/generate-uv-api-failed.log).

The initial open-preview script assigned Euler angles to imported quaternion-mode objects and therefore did not open them. The render script now explicitly sets imported hinge rotation mode to XYZ, then rotates both; corrected pixels were reviewed. Source and Three.js articulation tests independently pass. Front studio camera was adjusted slightly downward to avoid the backdrop horizon crossing the door.

The existing Vite shared-chunk size warning remains. Blender reports optional Draco unavailable; no Draco compression is requested or required. No existing tests were weakened.

## Preservation and scope

One appended catalog collection with one model, V2.1 P0 item 424, batch 5/10. Existing catalog values/order and all old model/source/evidence bytes are preserved. No app UI, architecture, schema, game or unrelated model changes. Existing approved previewCameraDirection is used; the source and GLB remain upright.

Original geometry/materials, owner-project reuse authorized, public redistribution terms unspecified and download false. No push, PR, merge, deployment or release.

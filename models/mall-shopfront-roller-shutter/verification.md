# Mall Shopfront Roller Shutter verification, 2026-11-12

## Result

**Local asset visual approval: PASS.** Actual-export closed/front/rear/part-open/open and explicitly labelled mechanism-cutaway renders were inspected, along with gallery screenshots. The metal curtain, dark U-guides, hood and bottom rail are recognizable. Open previews actually wind each slat, rather than hiding the curtain. No clipped bounds, unintended detached large parts or visible z-fighting were observed in reviewed views.

**Overall: NEEDS REVIEW for physical Android/iOS coverage only. Physical Android/iOS: NOT TESTED.** Desktop viewport emulation does not establish native browser, GPU, touch or performance behavior. The gallery is a static viewer, not a runtime shutter controller.

## Measured deliverables

- GLB 252,888 bytes, 4,608 triangles, 9,144 vertices, 44 mesh primitives, 4 materials.
- No textures, external resources, animations, exported cameras/lights or decoder dependency.
- Bounds 3.296 × 3.338 × 0.690 m; minimum glTF Y=0.
- Curtain width 3.0 m, 28 slats at 0.10 m pitch.
- Guide-lip clear width 2.92 m; full-open floor clearance 2.60 m.
- GLB SHA-256: 0cdb6d5fd565760a01fb9a1c491249afe8f54e40654ae2ab2080a6e772d4f077.
- Source SHA-256: df05a3d25a552937e87058826fd27570af495d556c9cdd9e448b89cf6187f126.
- Six 768 × 768 PNGs and corresponding WebPs; WebPs 14,374–43,202 bytes.

## Executed gates

| Gate | Result | Evidence |
| --- | --- | --- |
| Khronos glTF Validator | PASS, 0 errors / 0 warnings | reports/assets.json |
| Bounds, scale, roots, components, metrics and budgets | PASS | validate.mjs |
| Geometric winding at 53 lifts, 0–2.6 m in 50 mm steps | PASS | reports/articulation.json |
| Reopen source and positive-volume closed manifold parts | PASS, 44/44 | reports/sources.json |
| Real mesh/material edit, save and re-export | PASS, edited GLB 0/0 | reports/source-edit.json |
| Full Node units | PASS, 145/145 | reports/unit-final.log |
| Catalog validation + production Vite build | PASS | reports/build-final.log |
| Strict gallery 1440×900 / 768×1024 / 390×844 | PASS, 3/3 | reports/browser/results.json |
| Existing library regression | PASS, 9/9 groups | reports/library/results.json |
| Studio and browser pixel inspection | PASS | previews/ and reports/browser/ |
| Actual Android / iOS devices | NOT TESTED | No physical device evidence |

## Assembly and source editing

All 53 sampled poses use the real shipped GLB. Conservative oriented bounding boxes separate each slat from every other slat, the bottom rail, hood sheets and guide pieces. A separate segment-to-axis distance calculation verifies the full rectangular slat cross-sections clear the actual cylindrical drum. Fixed-frame world transforms remain unchanged, floor clearance follows the lift, and reset restores all original curtain transforms. Guide/hood attachment contacts and the intentional overlapping rail/seal attachment are not treated as defects. Sampled geometric tests are not a continuous collision, engineering safety or physical linkage certification.

The source independently reopens and poses closed, part-open, open and reset without moving the fixed assembly. The edit proof raises BOTTOM_Rail top vertices 2 mm and changes slat roughness from 0.38 to 0.5, then saves and re-exports an isolated source copy. All other mesh bounds and the shipped source hash remain unchanged. Both original and edited GLBs validate 0/0.

Four focused Node unit contracts rerun the live GLB validator and all 53 pose checks, then verify catalog/metadata metrics, independent parts, source hash/edit evidence, preview budgets and disabled-download rights. This makes the asset gate repeatable under npm test rather than relying only on saved reports.

## Browser evidence

156.0.8078.4 on Linux ARM64, headless SwiftShader. Exact response/consumed GLB bytes and SHA match the shipped GLB above; all GLB responses are HTTP 200. Each viewport checks positive WebGL draws, correct title, disabled download, orbit, zoom, exact reset, further orbit, close/exact reopen and no horizontal overflow. Requestfailed, console errors, page errors and HTTP errors are asserted empty, with no ERR_ABORTED filtering.

The unchanged library harness includes an inherited macOS label. Actual runtime is Linux ARM64 as recorded in reports/environment.json. It is not macOS or native mobile evidence.

## Corrections and retained failures

The first bounds gate caught a stale Blender matrix after cylinder rotation. The attachment helper now updates the dependency graph before preserving transforms, and the validator asserts the drum's axial dimensions. Initial failure is retained in reports/validate-initial.log.

The next gate caught an outward spiral crossing the incoming curtain at 1.45 m lift. The pose helper now winds inward from the outer feed radius so completed turns stay behind the incoming slats. reports/validate-winding-failed.log preserves the failure; all 53 final poses pass unchanged separation assertions. Initial render/generation logs are retained; delivered previews were rerendered after both corrections. The circular core remains stationary; no motor dynamics are claimed.

The inherited Vite chunk-size warning remains. Blender reports optional Draco unavailable; no Draco compression is requested. No existing tests were weakened.

## Preservation and scope

Catalog adds one collection and one asset, item 425, batch 6/10. All prior catalog values/order and all old model/source/evidence bytes are preserved. No app/schema/UI, game, architecture, dependency or unrelated model changes. Only the existing approved previewCameraDirection setting is used.

Original geometry and materials, owner-project reuse authorized, public redistribution unspecified, download false. Local commit only; no push, PR, merge, deployment or release.

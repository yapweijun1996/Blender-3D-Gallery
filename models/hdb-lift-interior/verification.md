# HDB Lift Interior verification

V2.1 backlog **303**. **Local asset PASS; overall NEEDS REVIEW** because physical Android/iOS browsers and devices are **NOT TESTED**. Desktop viewport emulation is not native mobile acceptance. No push, PR, merge, deployment or release is claimed by this preparation.

## Scope and source

1.80 × 2.46 × 1.70 m open-front cabin. Independent walls, floor, ceiling, rear handrail and four generic buttons. Ceiling diffusers are visual surfaces and do not illuminate surrounding geometry. Not a working elevator or accessibility/code specification.

Original Blender Python geometry and materials; no third-party model, artwork, texture or font. Original project helper reuse only. Reuse in the owner's projects is authorized; public redistribution terms unspecified and catalog downloads disabled. This is an HDB-inspired generic visual asset, not an official HDB model, surveyed estate, construction detail or safety/engineering certification.

- Metre scene units; Blender +Z up and -Y front export to glTF +Y up and +Z front.
- [Generator](generate.py), [editable source](sources/hdb-lift-interior.blend), [GLB](exports/hdb-lift-interior.glb).
- Independent mesh data, named parts and materials verified by actual Blender reopen in [source evidence](reports/source.json).
- Actual source edit and re-export passed, preserving original source: [proof](reports/source-edit-proof.json), [edited GLB](reports/source-edit.glb), [edited blend](reports/source-edit.blend). Source poses do not imply runtime interactivity.

## Geometry and budgets

[Structural validator](validate.mjs) and [measured evidence](reports/assets.json): **0 Khronos errors, 0 warnings**.
- GLB 83,812 bytes; 1,500 triangles; 17 mesh primitives; 5 materials.
- No external buffers/textures, animation clips, lights or cameras in GLB.
- 500 KiB / 12,000 triangles budget passes. Exact exported dimensions, named components and finite geometry are asserted. No geometry compression/decoder required.

## Render and browser evidence

- Three multi-angle studio previews rendered from the **actual shipped GLB**, then inspected visually, not proxy geometry. [Primary preview](previews/hdb-lift-interior.webp), [front](previews/front.webp), [alternate](previews/alternate.webp).
- Actual Gallery initial screenshots at all three widths were inspected; model silhouettes and parts are visible and fit the canvas.
- Strict Chromium **3/3 PASS**, version **156.0.8078.4**, at 1440×900, 768×1024 and 390×844. [Full results](reports/browser/results.json), [log](reports/browser.log).
- Exact consumed GLB byte count/SHA; HTTP200; WebGL draws; keyboard orbit/zoom; exact reset and close/reopen; no horizontal overflow; no unfiltered request/console/page errors. No retries-to-green or error filtering.
- Repository unit suite **169/169 PASS**, including four new structural tests; build/catalog validation **PASS**. Shared unchanged full logs: [unit](../hdb-staircase/reports/unit-full.log), [build](../hdb-staircase/reports/build.log). Build retains existing chunk-size warning.

## Limitations

No physical Android/iOS test, device performance measurement, runtime simulation or certification. The batch assembler must rerun the combined 10-model gate after integration. Existing source, catalog entries and historical evidence are preserved.

Studio refinement: initial interior renders were grainy. Their [three WebPs and log](reports/initial-studio/) are retained. An OpenImageDenoiser probe failed because the Blender build lacks it ([log](reports/denoise-probe.log)); no denoised result claimed. Final renders use a separate frontal studio fill and 128 Cycles samples, inspected after rerender. Geometry/materials and browser lighting were not changed.

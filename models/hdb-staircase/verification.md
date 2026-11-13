# HDB Staircase verification

V2.1 backlog **301**. **Local asset PASS; overall NEEDS REVIEW** because physical Android/iOS browsers and devices are **NOT TESTED**. Desktop viewport emulation is not native mobile acceptance. No push, PR, merge, deployment or release is claimed by this preparation.

## Scope and source

Two flights of nine closed wedge steps each give 3.00 m floor-to-floor rise; 0.28 m treads and 1.20 m flight width. Separate nosings and rail members, with explicit lower/upper floor connectors. Initial open-riser draft was refined after inspection; final shipped source/GLB uses closed concrete wedge steps.

Original Blender Python geometry and materials; no third-party model, artwork, texture or font. Original project helper reuse only. Reuse in the owner's projects is authorized; public redistribution terms unspecified and catalog downloads disabled. This is an HDB-inspired generic visual asset, not an official HDB model, surveyed estate, construction detail or safety/engineering certification.

- Metre scene units; Blender +Z up and -Y front export to glTF +Y up and +Z front.
- [Generator](generate.py), [editable source](sources/hdb-staircase.blend), [GLB](exports/hdb-staircase.glb).
- Independent mesh data, named parts and materials verified by actual Blender reopen in [source evidence](reports/source.json).
- Actual source edit and re-export passed, preserving original source: [proof](reports/source-edit-proof.json), [edited GLB](reports/source-edit.glb), [edited blend](reports/source-edit.blend). Source poses do not imply runtime interactivity.

## Geometry and budgets

[Structural validator](validate.mjs) and [measured evidence](reports/assets.json): **0 Khronos errors, 0 warnings**.
- GLB 210,560 bytes; 3,780 triangles; 91 mesh primitives; 3 materials.
- No external buffers/textures, animation clips, lights or cameras in GLB.
- 1 MiB / 30,000 triangles budget passes. Exact exported dimensions, named components and finite geometry are asserted. No geometry compression/decoder required.

## Render and browser evidence

- Three multi-angle studio previews rendered from the **actual shipped GLB**, then inspected visually, not proxy geometry. [Primary preview](previews/hdb-staircase.webp), [front](previews/front.webp), [alternate](previews/rear.webp).
- Actual Gallery initial screenshots at all three widths were inspected; model silhouettes and parts are visible and fit the canvas.
- Strict Chromium **3/3 PASS**, version **156.0.8078.4**, at 1440×900, 768×1024 and 390×844. [Full results](reports/browser/results.json), [log](reports/browser.log).
- Exact consumed GLB byte count/SHA; HTTP200; WebGL draws; keyboard orbit/zoom; exact reset and close/reopen; no horizontal overflow; no unfiltered request/console/page errors. No retries-to-green or error filtering.
- Repository unit suite **169/169 PASS**, including four new structural tests; build/catalog validation **PASS**. Shared unchanged full logs: [unit](../hdb-staircase/reports/unit-full.log), [build](../hdb-staircase/reports/build.log). Build retains existing chunk-size warning.

## Limitations

No physical Android/iOS test, device performance measurement, runtime simulation or certification. The batch assembler must rerun the combined 10-model gate after integration. Existing source, catalog entries and historical evidence are preserved.

Development note: the initial source-edit verifier had a malformed newline literal, fixed before successful assertions; no assertions removed. [Note](reports/development-note.txt).

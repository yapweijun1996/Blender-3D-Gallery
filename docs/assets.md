# 3D asset standard

Status: proposed contract; validate tooling and budgets with real assets before adoption.

Each interactive work must have a real, browser-inspectable glTF 2.0 GLB, not just a render. Keep a Blender source file and procedural generator when available and appropriate to share. Record Blender version, dependencies, invocation, seed where relevant and third-party attribution. Preview images must represent the exported model faithfully.

## Metadata

Each model should have a unique lowercase kebab-case slug, title, summary, description, controlled category, tags, creation date, author and creation method, Blender version, relative asset paths, license and attribution, measured metrics, and a `draft`, `validated` or `published` status. A publication date is recorded only when publication actually happens. Validate paths against approved public asset roots and treat displayed text as untrusted.

Suggested measured metrics are GLB bytes, triangle and vertex counts, maximum texture dimensions and animation clip count. Never invent metrics or infer a model's category or license from its filename. Source code and artwork may have different licenses.

## Export and admission

1. Use an intentional origin, scale and transforms; check mesh bounds, normals, UVs and texture references. Verify materials and effects survive glTF export.
2. Validate the GLB with the Khronos glTF Validator, inspect reported errors and warnings, and measure geometry and file sizes. Test any compression and its decoder on target devices.
3. Check image decoding, representative composition and asset paths. Inspect the actual model in the browser on desktop and mobile, including camera fit, rotation, zoom and reset.
4. Review provenance, rights, attribution and visual quality. Only approved, validated entries enter the published catalog; failures remain drafts.

Candidate budgets for measurement: prefer GLB files at or below 5 MiB and 100,000 triangles; review larger assets and require an explicit exception for materially larger files. Typical texture dimensions should not exceed 2048 pixels without justification. Prefer thumbnails under 150 KiB and posters under 300 KiB when visual quality allows. These are targets, not measured guarantees.

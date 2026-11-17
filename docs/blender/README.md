# Blender engineering knowledge

Research edition 1.1.0 · 2026-11-15 · Asia/Singapore. This handbook covers reusable Blender authoring and delivery practice. The native experiments use Blender 5.1.2; a different version needs its own calibration.

<!-- KB-SUMMARY-START -->
The canonical cross-project knowledge domain is kbid `blender`. It owns reusable bpy automation, geometry, architecture interfaces, UV/PBR, rigging, extensions, glTF export and verification knowledge. Project dimensions, brand content, tickets, release status and device-specific budgets belong to their project records. Registry Skills remain in their own registry; candidate Skill names are not installed capabilities. Distinguish official-source statements, version-specific experiments, engineering recommendations and untested behavior. A platform listing establishes a declared compatibility range, not a successful install or background workflow. A valid GLB establishes format conformance, not visual quality, interaction, rights or performance. Record source URLs, review date, tool versions and artifact hashes; recheck changing version information before use.
<!-- KB-SUMMARY-END -->

## Read by task

| Need | Authoritative chapter |
| --- | --- |
| Python, MCP, background processes and ownership | [Automation](python-mcp.md) |
| Meshes, modifiers, module dimensions and clearances | [Architecture and topology](architecture.md) |
| UVs, texture density, shader export and color | [Materials and UVs](materials-uv.md) |
| Bones, weights, Actions, slots and motion policy | [Characters and animation](characters-animation.md) |
| Studying a chibi head and checking an original character against its design | [Chibi head study](chibi-head-study.md) |
| Coordinate conversion, GLB packaging and rendering cost | [glTF and runtime](gltf-runtime.md) |
| Independent checks, evidence and release boundaries | [Quality and delivery](quality-delivery.md) |
| Extension admission and the five reviewed candidates | [Extensions](extensions.md) |
| Reusable asset interfaces and source editability | [Asset contract](asset-contract.md) |
| Learning exercises and proposed Skills | [Roadmap](roadmap.md) |

The chapter between `KB-SUMMARY` markers is the source for its existing KB reference item. Longer procedures stay in their chapter; the dated extension catalog and calibration report also have separately chunked KB documents. This keeps existing item identities while extending useful retrieval.

## Evidence and limits

[Sources](sources.md) distinguishes version-pinned manuals, dynamic references, official extension listings and local experiments. Some direct manual requests were blocked; reviewed official search-index excerpts and the native API/exporter supply the stated evidence. The MCP server's bundled RST excerpts do not expose a documentation version; do not assume it matches the connected application.

[Calibration results](verification/probe-results.json) cover context polling, mesh sharing, coordinate conversion, exported vertices, scalar PBR factors, animation sampling, unit-scale behavior and CLI exception propagation. They do not establish character deformation quality, texture appearance, extension registration, phone compatibility or frame rate. No extension was installed by this research.

The [calibration note](calibration.md) retains a failed test assumption and its uniform correction. [Project evidence](../verification/foundation-v1/module-fit/README.md) illustrates a broader workflow, but its measurements are not generic Blender defaults.

## Maintenance

Update the owning chapter first, run relevant probes, then prepare and review its KB payload. Preserve existing KB IDs/categories and private visibility; read current metadata before replacing it. Verify content after writing and run representative retrieval questions. Updating this handbook does not register a Skill, change a scene, install an extension, or authorize a Git release.

[Character study closeout — 2026-11-17](2026-11-17-closeout.md) records the completed portrait, reusable Skill, KB maintenance and verification limits.

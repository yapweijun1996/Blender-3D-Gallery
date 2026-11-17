# glTF export and runtime cost

<!-- KB-SUMMARY-START -->
glTF linear distances are metres. With the tested Blender 5.1.2 +Y-up export, Blender (x,y,z) maps to glTF (x,z,-y); verify a known asymmetric object instead of guessing facing. In this fixture, changing scene scale_length to 0.01 alone leaves exported geometry unchanged, so enforce the intended physical size explicitly. Select export roots/descendants and exclude studio objects. Verify external resources and required extensions even for a GLB. Compare exported triangles, vertices, materials, textures and clips, not only Blender counts. Mesh sharing can reduce storage without reducing draw calls; runtime instancing/batching needs its own implementation. Transparent ordering and moving hierarchies constrain merging. Measure frame time, bytes and memory separately from draw calls. Pin the consumer, decoder dependencies and graphics backend. A desktop viewport is not physical-phone acceptance.
<!-- KB-SUMMARY-END -->

## Coordinate and resource boundaries

The [Khronos specification](https://registry.khronos.org/glTF/specs/2.0/glTF-2.0.html) defines units and node transforms. Asset facing and an application's navigation direction are separate contracts. Inspect world transforms, especially after parenting, negative scale or animation.

The generic fixture exports a Blender object centred at `(4,-5,6)` with dimensions `(1,2,3)`. The independently loaded GLB has centre `(4,6,5)` and dimensions `(1,3,2)`. The unit-scale observation applies to this exact exporter/options combination; it is not a claim about every exporter.

Use an explicit selection and review actual binary output. A GLB container does not alone establish that every image/buffer is embedded or that a required extension has a decoder in the consumer. Preserve the editable source when applying delivery-only modifiers or baking.

## Optimize by bottleneck

| Evidence | Useful response | Trade-off to inspect |
| --- | --- | --- |
| Many repeated geometry/material combinations | Runtime [InstancedMesh](https://threejs.org/docs/pages/InstancedMesh.html) or an equivalent mechanism | Per-instance bounds, updates, picking and animation |
| Many static material-compatible pieces | Spatial/material batches | Coarser culling, picking and independent visibility |
| Transparent overlap artifacts | Preserve appropriate sorting layers | Merging can change ordering; opacity edits can change the design |
| High texture residency | Appropriate dimensions/format/mips | Decoder support, quality and upload cost |
| Large meshes or skinning cost | Measured LOD/deformation simplification | Silhouette, weights and motion quality |

The [renderer](https://threejs.org/docs/pages/WebGLRenderer) and [material](https://threejs.org/docs/pages/Material.html) documentation explain sorting and multi-pass transparency. Do not infer a guaranteed speedup from a lower object count. Attribute `drawCalls`, triangles and frame-time results to the measured build/view/backend; a software-renderer timeout is not a successful hardware-independent result.

Structural validation and an independent loader check are in [quality and delivery](quality-delivery.md). Neither establishes visual browser compatibility by itself.

## Deployment input closure

A model catalog alone may omit resources needed by an application. The gallery additionally imports shelf LODs, manifests, character customization code and Solar demo GLBs. Its deployment selector combines catalog paths with literal model references and Vite globs. Compare a minimal checkout's complete production output with the regular checkout after changing this selection logic.

An exact build-cache identity must include the selected file paths and their committed blob identities. File byte counts or a catalog timestamp do not identify the content. The [deployment contract](../deployment.md) records cold and cache-hit runs, published build identity checks and the scope of the parser.

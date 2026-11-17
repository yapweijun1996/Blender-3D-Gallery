---
name: glb-lossless-png
description: Reduce embedded PNG bytes in exported GLBs while preserving decoded pixels, colour metadata and non-image buffers. Use for lossless gallery download optimization and its independent validation.
---

# Lossless GLB PNG optimization

Use the existing `scripts/optimize-glb-png.py`. Read [the tool contract](../../../docs/tools.md#glb-lossless-png-recompression) and [batch evidence](../../../docs/verification/model-downloads/batch-02/README.md).

1. Rank actual catalog exports by bytes. Exclude assets already processed unless a source changed. This encoder handles embedded single-frame, 8-bit RGB/RGBA PNGs in a single-buffer GLB. Choose a different reviewed method for JPEG, WebP or geometry compression.
2. Work on approved copies in an isolated checkout. The script replaces supplied files and writes its final report after the batch. A failure can leave earlier files changed. Preserve the original Git revision and inspect the resulting diff.
3. Use Python and the documented Pillow version. Pass explicit GLB paths and `--report`. Use only outputs that are smaller. A larger candidate leaves its original file intact.
4. Keep each PNG's non-IDAT chunks byte-identical, including its header, sRGB/gamma/chromaticity, EXIF and physical dimensions. Independently compare decoded pixels, mode, dimensions and metadata. Encoding a visually similar PNG is insufficient.
5. Independently parse original and final GLBs. Compare every non-image buffer payload and all node, scene, mesh, accessor, material, texture, sampler, skin, morph and animation definitions. Buffer packing offsets and lengths may change. Run the pinned Khronos validator and review its actual messages.
6. Refresh any source hashes and byte counts in derived manifests. Run the affected source/export relationship tests. In this gallery, `models/solar-demo/manifest.json` identifies the sources of the smaller scene models.
7. Build and render the actual source and candidate GLBs in the same browser, camera, lighting and pose. Compare canvas pixels at representative desktop and phone viewports. Exercise relevant arm, skin, skeleton or animation states. Verify consumed hashes in the viewer.
8. For large responses, Playwright's inspector response body may be evicted. Hash the actual `Response.arrayBuffer()` consumed by the loader instead of treating an unavailable inspector body as evidence of a bad GLB.
9. After an authorized push, verify successful deployment, live build identity and every changed public GLB hash. If an installed service worker serves the old index, apply the site's visible update flow and recheck the resource graph.

A smaller GLB demonstrates transfer-byte savings. Keep physical-device performance and broader model-quality claims tied to separate measurements.

# UV mapping, texture density and exportable PBR

<!-- KB-SUMMARY-START -->
Separate color textures from numerical data. Base-color/emissive textures use their intended color encoding; metallic, roughness and normal data require non-color interpretation. The glTF metallic-roughness convention places roughness in G and metallic in B. Use exporter-recognized Principled BSDF connections, then inspect the emitted material; an arbitrary Blender node graph is not a portable shader. Tangent normal maps need the correct convention and matching UV map. Assess UV distortion, orientation, margins and density at the intended viewing distance. Intentional mirrored/stacked UVs require a stated use case. Bake unsupported procedural appearance when appropriate and preserve image sources/licenses. Texel density is not a guarantee of readable packaging. In the 5.1.2 calibration, scalar roughness/metalness survive export and UV seams increase the smooth cube's exported vertices from 8 to 14.
<!-- KB-SUMMARY-END -->

## Mapping and legibility

Review each asset's text orientation, seams, islands and mip-safe padding. Packing fills space; it does not by itself equalize density. [Average Island Scale and packing](https://docs.blender.org/manual/de/5.1/modeling/meshes/uv/editing.html) address related but different problems.

For a uniformly scaled UV patch, a useful area-average estimate is `sqrt(UV_area * image_width * image_height / world_area_m2)` texels/metre. It does not detect directional stretching, and non-square images deserve an axis-aware visual check. Treat this formula as an engineering estimate, not a readability threshold.

## Material transfer

The [5.1 glTF material documentation](https://docs.blender.org/manual/en/5.1/addons/import_export/scene_gltf2.html) describes recognized node connections. Keep numerical maps out of color conversion. The [Normal Map node](https://docs.blender.org/manual/en/5.1/render/shader_nodes/displacement/normal_map.html) distinguishes OpenGL/DirectX conventions and UV requirements. A numeric base-color factor and an encoded image are different representations.

The fixture verifies scalar factor transfer, not texture decoding or lighting. A browser check should inspect actual decoded images under recorded lighting and tone mapping; a Node stub that reads PNG dimensions cannot establish appearance.

## Baking and delivery

Bake only the channels required by the delivery contract. The [Cycles baking manual](https://docs.blender.org/manual/en/5.1/render/cycles/baking.html) explains active image-node targets and edge margins. Preserve the procedural source and bake settings, not only the resulting PNG. Recheck the GLB after export, because its packed image/channel layout can differ from the authoring view.

[Texel Density Checker](https://extensions.blender.org/add-ons/texel-density-checker/) can assist this work. Its official listing is verified; execution in this project's UI or background environment has not yet been tested.

## Lossless PNG delivery

Pixel equality alone does not prove unchanged colour interpretation. The tested GLB optimizer replaces only PNG IDAT chunks and preserves all other chunks byte-for-byte, including sRGB, gamma, chromaticity, EXIF and physical dimensions. It requires an identical header and independently compares decoded pixels, dimensions, mode and metadata. Non-image GLB buffers and scene/material/skin/animation definitions need their own comparisons.

The recorded profile is embedded, single-frame 8-bit RGB/RGBA PNG in a single-buffer GLB. A candidate is adopted only when smaller. A smaller transfer payload does not establish lower texture memory or faster rendering. See [tool contracts](../tools.md) and [the two measured batches](../verification/model-downloads/README.md).

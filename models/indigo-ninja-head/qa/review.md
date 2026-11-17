# Independent review of the exported ninja head

The review uses the actual GLB in Three.js, viewed from the front, 35°, 90° and back with the same orthographic camera and lighting. This original design has no supplied character sheet. The visual checks cover the swept quiff, expression, headband mark, profile, rear hair coverage and scarf.

## First pass

The [first GLB report](round-01/report.json) records 53,976 triangles and zero Khronos validation errors or warnings.

- The [front](round-01/front.png) shows a readable pair of amber eyes, a slight smile and a visible twin-slash badge. The large front locks establish a diagonal sweep. The broad rounded ends that sit directly on the headband make the locks look individually planted.
- The [profile](round-01/profile.png) shows a clear nose, ear and chin. Several short hair sections sit apart on a large, smooth skullcap, which interrupts the flow from the crown towards the nape.
- The [back](round-01/back.png) shows isolated teardrop locks and a level cap edge above a broad strip of skin. The requested correction was to extend and overlap the hair masses from the crown through the nape.
- The scarf has a jagged red boundary on its front-left and rear-right surfaces. The requested correction was a clean wrap overlap with a tapered end.

## Second pass

The [second GLB report](round-02/report.json) records 75,334 triangles and zero validation errors or warnings. The same-camera renders show the scarf overlap now tapering cleanly, the brows and lids giving the gaze a clear direction, and the lower side hair tracing the ear and back of the skull. At 100 pixels the swept crest and scarf retain distinct silhouettes. The gold badge is visible at this scale, with its engraved detail easier to read in a close-up.

The [back](round-02/back.png) shows a continuous layer of pointed nape hair. A broad horizontal bulge above it interrupts the flow from the crown. The suggested refinement was to overlap that band with diagonal locks of different lengths.

## Final pass

The [final back](../previews/runtime/back.png) shows diagonal locks continuing from the crown through the nape. They overlap the area that formed a horizontal ridge in the preceding version. The [profile](../previews/runtime/profile.png) retains a distinct nose, ear and chin. The [three-quarter view](../previews/runtime/three-quarter.png) preserves the side glance, raised brow, swept crest and gold mark. The scarf wraps cleanly across the front and back. These features pass independent visual review for this original stylized bust.

The [100-pixel avatar](../previews/runtime/avatar-100.png) and [solid silhouette](../previews/runtime/silhouette-100.png) were rendered directly from the GLB at 100 × 100. The large quiff, head and collar remain distinct. The badge's tiny markings need a larger presentation. The [comparison](../previews/runtime/round-comparison.jpg) pairs first and final images from matching cameras, including the native Blender hero and three runtime views.

The [final report](report.json) records SHA-256 `b07945b0baf4bf80c9b4b4f898fa958b5c8763051785795ed63822d4f96a6452`, 67,414 triangles, 82 meshes and 27 materials. The 1,144,052-byte GLB stores its resources internally and uses material colors. Khronos validation recorded zero errors and warnings, with informational messages for an unused UV attribute and an empty node. The WebGL captures cover static appearance in desktop Chrome at two output resolutions.

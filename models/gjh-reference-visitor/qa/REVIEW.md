# Reference and rig QA

Status: **REWORK** for production use. The exact reviewed source, export and images are identified in `manifest.json`; the Khronos report and measurements are in `technical-rigged.json`.

## Independent visual review

The independent reviewer compared the provided character sheet and the front, side, back and three-quarter source views. The oversized head, friendly face, ivory and purple clothing, purple-and-white shoes, backpack and bag marks read as a coherent chibi. The original chest mark was hidden, then floated away from the shirt; projection fixed both. Gaps in the long sleeves were covered. Two iterations of the shorts addressed an overly padded construction and a later box-like shape. The reviewer confirmed those corrections in the final source turnaround.

Remaining differences: the rear hair is layered and pointed compared with the reference, the top tuft is thin, the backpack is more rectangular, the front straps are short, and tiny purple remnants appear near the shoulder seam. The front collar is lighter than the reference's purple hood. This is a stylized interpretation rather than a faithful reconstruction of every feature.

The reviewer separately compared Blender captures of the exact re-imported GLB at rest, walk frame 8 and sit frame 31 with source captures. These sampled views were visually consistent. They do not establish quality over a complete animation cycle.

## Technical and animation

- GLB validation: zero errors and zero warnings; 17 informational messages. See `technical-rigged.json` for the exact export hash and details.
- Default height: about 1.295 m. Nine joints; five named draft clips. No expression morphs.
- 56,736 triangles and 17 materials: exceeds the sheet's proposed 1,500–3,000 triangles and 4–6 materials, and the project draft's 40,000-triangle budget.
- Sitting is not accepted: the leg intersects the shorts, the body does not establish contact with a seat, and the pose reads as suspended. The one-frame walk and run captures do not demonstrate continuous foot contact, timing or absence of sliding. Shoulder deformation is limited by the inherited combined torso/sleeve topology.
- Runtime animation in a separate game engine or browser, the untested expression requirements, whole-cycle motion checks, and reproducible rebuild equivalence are NOT_RUN.

An earlier GLB produced 27 `NODE_SKINNED_MESH_NON_ROOT` warnings. The retained alternate export bakes transforms on temporary copies to put skinned meshes at the root. Blender's exporter emits a separate parent-selection warning for these root meshes; validator and the sampled re-import checks are recorded above.

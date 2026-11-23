# GJH modular chibi visitor

An editable Blender character based on the user's GJH Virtual Mall Chibi Visitor sheet. The model retains the classic purple-and-ivory hoodie, shorts, shoes and backpack, with optional hat and jeans. It builds on the repository's `chibi-visitor-v4` head and hair helpers; the user's reference is not embedded.

## Deliverables

- `sources/gjh-reference-visitor.blend`: editable master with the model collection, 19-bone rig and five draft actions. Optional garments are hidden in the `GJH Optional Wardrobe` collection.
- `exports/gjh-reference-visitor-rigged.glb`: full character, including per-part `extras.partSlot` metadata.
- `exports/modules/`: 38 standalone skinned slot GLBs and `manifest.json`. See `MODULES.md` for attachment, switching and variant conflicts.
- `exports/gjh-visitor-hair.glb`: optional rigid, static hair-only GLB; `exports/modules/hair.glb` is the skinned module.
- `qa/modular-rework/`: current visual and hash-bound technical evidence. Earlier QA documents and images describe earlier exports, not this version.

The eyes, brows and mouth are replaceable UV-textured surface patches; ears and nose are separate meshes. Each finger is a separate mesh with one rigid bone. Hiding an ear still leaves a skin-coloured underlay; shoulder ends and wardrobe transitions are simplified. None of the facial parts are expression morphs.

Hair has 8,876 triangles versus 62,860 in the preceding version. The full character has 51,543 triangles and 24 materials, exceeding the reference sheet's 1,500–3,000 triangles and 4–6 materials. Its rear hair remains more regular and rounded than the reference; crown tips are simplified. The existing sit animation intersects the shorts and lacks verified seat and foot contact. Other clips remain drafts; sampled skeleton and module tests do not establish continuous motion quality.

## Rebuild

The original `build.py` uses Blender 5.1.2 and the existing `models/chibi-visitor-v4` source; it constructs the base, not the full modular master. To recreate the current modular work in a fresh Blender scene, run the initial build and rig, then in order run `modular_wardrobe.py`, `create_modular_fingers.py`, `create_body_core.py`, `redesign_hair_v2.py` and `modularize_face.py`; save the master, then run `export_hair_module.py`, `export_rigged.py` and `export_modules.py`. The scripts and v4 dependency are in the repository and are not included in the delivery ZIP; they write fixed output paths, so back up existing outputs before rebuilding. A byte-identical rebuild has not been verified. The original fused head and hands remain in hidden source-only collections.

For exact current hashes, validation and the scope of the performed checks, see `qa/modular-rework/REVIEW.md` and its linked JSON reports. A format-validator pass is not a claim that the model meets the reference budget or that all motion and garment interactions are ready for production.

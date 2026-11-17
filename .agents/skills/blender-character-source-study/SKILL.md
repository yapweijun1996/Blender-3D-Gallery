---
name: blender-character-source-study
description: Compare a public or user-provided Blender character generator with its saved .blend and orthographic views to identify how a head, eyes or hairstyle was actually built. Use for hands-on source studies and reusable modeling lessons.
---

# Study an editable character source

1. Record the generator commit, model path and license. Trace the active builder from its entry point through the face and hair calls. Look for early returns, optional branches, later joins or renames, hidden collections and differences between source and saved release. Label code observations and saved-scene findings separately.
2. Inspect the saved file in an isolated Blender process with automatic script execution disabled. Read the source as data. Avoid running a third-party generator merely to list what is in its saved release. Discover target collection names in the actual scene first. The bundled read-only inspector checks selected collections recursively in the active scene and reports exact object names, original mesh vertex counts, evaluated world-axis bounding-box sizes, source SHA-256 and Blender/file versions. It retains hidden objects as inventory; render visibility needs a separate check.

   ```sh
   printf '%s\n' '{"source_file":"/path/to/reference.blend","collections":["Hair"],"expected_objects":["Fringe"]}' | python3 scripts/inspect_blend_collections.py
   ```

   Run this from the skill directory, on a host with Blender installed. A missing name is reported in the JSON with `matches_expectations: false`. A file written by a newer Blender can be readable with a compatibility warning; record the versions and preserve the original. For an unexpected name, inspect the release collection and object identities before inferring a missing design feature.

3. Use one orthographic camera for the dressed head profile and an isolated head-surface profile at the same position and scale. Add an oblique view of brow, lids, cheek and hair overlap. Inspect the actual images. Call out which contours come from the face surface, swept locks, a continuous cap or thin face-conforming layers. In Workbench, vertex-color or node-based eye shading can look different from the authored render. Document lighting and any isolation.
4. When applying a technique, adapt it to the requested silhouette. For instance, guide width, thickness and tip taper independently along a swept lock. Use side, oblique and rear views to judge skull clearance and contact with the hair cap. Keep inferred depth from a single poster labeled as a design decision.
5. When GIF and GLB are requested, bind each deliverable, source camera, frame sequence or clip and major transforms to the source/export hashes. Compare a named GIF frame with the same pose and view from the exported GLB. Independently rotate the exported model: hair tips, eye layers, nose and jaw should still read from the side. A GIF alone demonstrates a sequence of rendered images; validate GLB structure and open it in the intended viewer to establish interactive behavior.
6. Report the exact source lines, actual saved object names, inspected views, modifications made for capture and limits. Credit retained or distributed study images under the asset's license. Treat conclusions about likeness, deformation and compatibility as independent questions that require their own evidence.

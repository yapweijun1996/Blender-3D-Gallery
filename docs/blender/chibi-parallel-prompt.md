# Build a chibi character with Codex CLI and Blender MCP

Use this as the lead agent's task. The reference image attached to the CLI prompt sets the character design. If the operator also supplied a path to it, give that path to each worker so everyone can inspect the same artwork.

## Establish the shape together

Make one full-body chibi human for local review. Choose a fresh output directory under `output/` for this run. Use Blender MCP to inspect the connected scene. Preserve the open artwork and its file. Work in a separate character scene. When saving the standalone master, include only its character and studio setup.

Read the reference yourself. Pick three features that identify this particular person, such as the sweep of the fringe, the shape of the cheeks, or a distinctive collar. Note which side carries any asymmetric accessory, using the character's own left and right.

Build a simple grey proxy and compare it with the reference at matching front and side angles. Adjust the head width, cheek and chin profile, shoulder width and leg length while the forms are still simple. Share that proxy, the reference path, the palette, and one small file of dimensions with all workers. Use metres, +Z up, −Y forward, and place the soles at Z=0. Record the neck centre and radius, shoulder centres, pose, and wrist positions. Set proportions from the reference. About 2.5 heads tall is a starting point for an original toy-style design.

## Spawn three subagents in parallel

Give each worker a separate directory under the run folder. The lead agent owns the master scene and is the only writer to the live Blender MCP session. Workers can build and render their part using local Blender in background mode with their own output files. Share a read-only copy of the proxy. Keep each part in the proxy's coordinates.

| Worker | Responsibility | Handoff |
| --- | --- | --- |
| Head | Model the face, eyes, ears, hair and headwear against the shared body and neck. Check eye placement in three-quarter view and the sweep of the hair from behind. | Editable head parts or a rebuild script, plus a front and a three-quarter preview. |
| Body | Model the neck, torso, limbs, clothing, footwear and hand-held accessories. Fit the collar to the head proxy. Check the costume and grounded stance from front and side. | Editable body parts or a rebuild script, plus a front and a side preview. |
| Reviewer | Read the reference, identify its visible landmarks, and prepare fixed cameras, neutral light and final GLB verification in an isolated scene or viewer. | A short list of features to inspect and repeatable captures. Later, independently review the assembled export. |

While they work, prepare the assembly and export in the run directory. Keep the preview camera scale, pose and lighting fixed across revisions. Route an interface change, such as moving the neck, through the lead and tell both builders before they continue. Wait for both parts before final assembly.

## Assemble, inspect, correct and deliver

1. Assemble the character in Blender through MCP. Inspect the actual viewport and capture front, three-quarter, side and back views. At thumbnail size, check whether the hairstyle, expression and outfit are recognizable. In a face close-up, check the eyelids, highlights and fringe. Use a plain clay material in a review copy to expose gaps and hair intersections hidden by colour.
2. Save an editable standalone `.blend` with the character's textures packed when applicable. Export a character-only `.glb`. Load the exact exported file in an independent viewer, run the installed Khronos validator and check the materials, orientation and feet. Record triangle count and file size. If the operator requests animation, agree on rest pose and bone names before delegation, then test the requested poses and expressions on the exported file.
3. Give the reviewer the reference and captures of the export. For each mismatch, name the angle, feature and visible defect. Route geometry corrections to the owning worker, reassemble, then repeat the same captures and review the corrected GLB.
4. Return the paths to the editable blend, GLB, preview sheet, and rebuild inputs. Report the checks actually run and any remaining visible differences. Keep the work local.

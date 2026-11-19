# Chibi explorer

A static procedural character study based on the [three-view design sheet](character-turnaround.png). The [Crucible 0.21.0 recipe](explorer.recipe.json) retains the editable shapes and materials. To reproduce the [GLB](explorer.glb), pass the recipe to `scene_create` and export that same session with `scene_export_glb` on a server configured with a jobs directory.

The [front, side and back comparison](gallery-views.png) shows the exported GLB in Chrome with the Gallery's Three.js viewer. The views look toward the character from +Z, +X and −Z respectively. The model has 40 parts and no animation clips.

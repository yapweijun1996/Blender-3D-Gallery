# Game-ready vehicles · Set C

The six GLBs derive from the gallery exports identified by path and SHA-256 in
[contact-sheets/manifest.json](contact-sheets/manifest.json). The comparison
sheets show the original and the exact game GLB from the same six camera
positions. All dimensions in [models.json](models.json) include protrusions
such as mirrors.

## Runtime use

- Meshes are in metres, Y-up and forward along +Z. The local origin of
  `body` is centered on the ground footprint. The four `wheel_*` meshes
  are centered on their respective axles and spin around local X.
- Tint the `paint` material by changing its base color factor. Trim,
  glazing, livery and lamp colors use constant, untextured face colors
  through the glTF vertex color attribute.
- The taxi sign and the police bar share the `light` material with the
  other lamps. The material extras list the component names. The
  light primitive's extras record the corresponding index ranges in
  triangles, starting at zero.
- The lorry bed is in its lowered position and merged into `body`.
  The GLBs are static assets. Collision and vehicle controls belong to the game.

## Rebuild

From this folder, run the following commands sequentially. The launcher defaults
to the task's Blender installation and uses two threads. Set
`VEHICLE_BLENDER_DIR` to another installation with the same layout if needed.

```sh
sh run_blender.sh build.py
node validate.mjs
sh run_blender.sh render.py
```

The original gallery exports and their license files remain in their model
directories.

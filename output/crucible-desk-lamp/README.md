# Low-poly desk lamp

An original static desk lamp built with Crucible MCP 0.21.0. It uses a flared enamel shade, a two-link arm, brass hinge pins, a recessed reflector, and an opal bulb. The lamp measures approximately 255 × 331 × 180 mm in glTF X, Y, Z order.

- [Editable Crucible scene recipe](desk-lamp.recipe.json)
- [GLB](desk-lamp.glb)
- [Crucible review grid](crucible-review.png)
- [Gallery viewer screenshot](gallery-view.png)

Start the Crucible MCP server with a local Chrome installation and a configured `--jobs` directory. Pass the JSON recipe to `scene_create`, then pass the returned session ID to `scene_export_glb`. The GLB contains the static mesh and materials.

The first export distorted parts that combined rotation and nonuniform node scaling. The final recipe uses extruded arm contours and dimensioned lathe profiles for the hinges. All 15 exported node matrices matched the authored transforms within 0.000001 per element.

Khronos glTF Validator reported zero errors and zero warnings. The final 60,772-byte file contains 1,464 rendered triangles across 15 mesh nodes. Chrome loaded the GLB through the Gallery's normal model dialog using a temporary local catalog entry. Keyboard rotation and zoom changed the rendered view, Reset restored the original frame pixel for pixel, and the test produced no browser console errors or warnings.

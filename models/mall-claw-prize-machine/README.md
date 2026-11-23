# Mall Claw Prize Machine

Original, metre-scale indoor arcade cabinet with an arched lavender/vanilla marquee, three-sided clear acrylic, a two-axis trolley and cable, three open claw fingers, and six unbranded prize toys. The toy forms, stitched eyes, ears, bill and limbs are modeled rather than painted on a plane. The front collection opening has recessed walls, a floor and a posed flap. Service panels, window hinges, door lock and joystick/button hardware are modeled parts.

- `mall-claw-prize-machine.blend` is the editable assembly. Each claw finger has named links, gripping pad, pivot pins and actuator strut. The authored pose is fixed, not rigged; the separable parts can be edited in Blender.
- `exports/mall-claw-prize-machine.glb` is a static, material-batched viewer model, with +Y glTF up and a floor-level origin. Front is Blender -Y. No camera, floor, lights or authoring-only files are exported.
- `previews/studio.webp` is a true 512 px studio render of the same geometry.
- No payment, button behavior, prize play, GLB animation, commercial branding or game integration. Public redistribution terms are not specified, so the Gallery download control is disabled.

## Reproduce and verify

From the repository root with Blender 5.3.0, WebP tools and the locked Node dependencies:

```sh
blender -b --python-exit-code 1 --python models/mall-claw-prize-machine/generate.py
cwebp -quiet -resize 512 512 -q 86 models/mall-claw-prize-machine/previews/studio.png -o models/mall-claw-prize-machine/previews/studio.webp
node models/mall-claw-prize-machine/verify.mjs
blender -b models/mall-claw-prize-machine/mall-claw-prize-machine.blend --python-exit-code 1 --python models/mall-claw-prize-machine/verify_blender.py -- models/mall-claw-prize-machine/exports/mall-claw-prize-machine.glb
```

The Blender script checks the editable assembly and reimports the GLB to independently measure its actual geometry. Metadata pins the checked-in hashes; regenerated outputs should be remeasured if the export or WebP tooling changes. Any generated studio PNG and Blender backup remain local derivatives.

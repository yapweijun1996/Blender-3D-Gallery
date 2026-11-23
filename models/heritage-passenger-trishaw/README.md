# Heritage Passenger Trishaw

Original metre-scale, Southeast Asian heritage-inspired passenger cycle with a sidecar layout. A conventional two-wheel bicycle carries a passenger sidecar on a third outboard wheel. Three spoked wheels, a swept handlebar, curved steering fork, chainrings, closed roller chain, crank arms, pedals, rim brake hardware and mudguards are actual modeled parts. The passenger cabin has a padded seat, hardwood step, curved grab rails and a striped fabric canopy on bowed hoops.

- `heritage-passenger-trishaw.blend`: editable groups, individual wheel spokes and drivetrain parts, and studio setup. Front is Blender -Y.
- `exports/heritage-passenger-trishaw.glb`: static material-batched inspection model, +Y glTF up and near-floor origin. No camera, lights, floor, animation or simulated motion.
- `previews/studio.webp`: real 512 px Blender render of the same geometry.
- This is an original interpretation, not a replica of a specific historical vehicle or an operational road-safety design. No logos, third-party model or asset, gameplay or route integration. Redistribution terms are unspecified, so the Gallery download control is disabled.

## Reproduce and verify

From repository root with Blender 5.3.0, WebP tools and locked Node dependencies:

```sh
blender -b --python-exit-code 1 --python models/heritage-passenger-trishaw/generate.py
cwebp -quiet -resize 512 512 -q 86 models/heritage-passenger-trishaw/previews/studio.png -o models/heritage-passenger-trishaw/previews/studio.webp
node models/heritage-passenger-trishaw/verify.mjs
blender -b models/heritage-passenger-trishaw/heritage-passenger-trishaw.blend --python-exit-code 1 --python models/heritage-passenger-trishaw/verify_blender.py -- models/heritage-passenger-trishaw/exports/heritage-passenger-trishaw.glb
```

The Blender script checks the editable assembly and independently reimports the GLB to measure its actual vertex bounds. Metadata pins the checked-in hashes. The generated PNG and Blender backup are local derivatives, not Gallery assets.

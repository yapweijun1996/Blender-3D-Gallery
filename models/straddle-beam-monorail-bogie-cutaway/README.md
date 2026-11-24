# Straddle-Beam Monorail Bogie Cutaway

Original static tabletop exhibit inspired by Kuala Lumpur's monorail context. A short concrete beam supports the two larger rubber running tyres on its **top**. Separate horizontal guide and stabilizer tyres meet **both sides** at two levels. The exposed saddle frame, pins, hubs and contrasting cut face are separately editable. This is a fictional arrangement, not a model of a specific Malaysian vehicle, structure or operational system, and not construction, loading or safety guidance.

- [Prasarana Malaysia, About Us](https://www.prasarana.com.my/about-us/) and the [Ministry of Transport, Current Rail Services](https://www.mot.gov.my/en/land/infrastructure/current-rail-services) document the local KL Monorail context only.
- [Hitachi Review, Straddle-type Monorail Systems](https://www.hitachihyoron.com/rev/pdf/2004/r2004_01_105.pdf), and [Hitachi's historic diagram of load, guide and stabilizing wheels](https://www.hitachihyoron.com/jp/pdf/1965/04/1965_04_22.pdf), explain the general straddle-beam concept. All geometry, proportions, finish and renders here are original; neither source is claimed to describe this model or KL's particular hardware.

## Reproduce and verify

Run locally from this folder (Blender 4.3.2). Blender -Y is front and +Z up; GLB +Z is front and +Y up. No animation or textures are needed.

```sh
blender -b --python-exit-code 4 --python generate.py -- --output ./generated
blender -b --python-exit-code 5 --python verify_blender.py -- ./generated
node verify.mjs ./generated/exports/straddle-beam-monorail-bogie-cutaway.glb
```

Use `--skip-render` to generate just the source and GLB. Actual native and independently reimported mesh rays check distinct contact planes, and the shipped Three.js loader checks the same contact groups against the export.

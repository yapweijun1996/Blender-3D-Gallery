# Mall escalator floor transition · 2 m

This 2.00 × 0.12 × 0.10 m closure fits between either end of the original escalator and the 2 m floor slab. Its editable source is a single closed mesh per level of detail. The two graphite and steel finishes share the same flat walking surface as the champagne-metal shoulder caps.

## Installation

Local glTF +Y is up and +Z points from the escalator toward the slab. Place the pivot at the midpoint of the outer tread edge at its finished height. The part spans X = −1 to +1, Y = −0.100 to 0 and Z = 0 to +0.120 m. Its centre pocket extends from X = −0.780 to +0.780, Z = 0 to +0.025 and from the underside up to Y = −0.015 m. With the original 1.55 m-wide beam, this leaves 5 mm of clearance on each side, behind and above the projection.

| End | Transition origin (X, Y, Z) | Transition yaw | Adjoining slab origin (X, Y, Z) |
| --- | --- | --- | --- |
| Lower | (0, 0, +5.441056) | 0° | (0, −0.100, +6.561056) |
| Upper | (0, +3.000, −5.441056) | 180° | (0, +2.900, −6.561056) |

Each shoulder extends 225 mm past the deck. Its inner 5 mm retains the thin roof of the beam recess. The remaining 220 mm closes the full 100 mm depth. The wear plate wraps around the front, side and top. Each front carries two countersunk steel fixings at LOD0 and LOD1. The head faces are flush, and the annular seats recede 0.55 mm into the face. The far slab edge, outside side faces and whole top remain on their installation planes. The floor beside the 1.55 m escalator requires its own support. [Original joint measurements](../../docs/verification/mall-escalator-floor-joint/README.md)

## Authoring and verification

LOD0 uses 16-sided fixings, three traction strips and paired fine registration lines. LOD1 keeps the three strips and reduces the fastening and edge detail. LOD2 retains two strips, the shoulder finish and its dark front registration band. The three levels preserve the complete stepped structural envelope.

With the repository dependencies and Blender 5.1.2, run the following from the repository root.

```sh
blender --background models/mall-escalator-floor-transition-2m/sources/mall-escalator-floor-transition-2m.blend --python-exit-code 1 --python models/mall-escalator-floor-transition-2m/inspect_source.py
blender --background --python-exit-code 1 --python models/mall-escalator-floor-transition-2m/generate.py -- --export-source --skip-render
node models/mall-escalator-floor-transition-2m/verify.mjs
```

Use `--rebuild` to regenerate the source and omit `--skip-render` to regenerate the studio JPEG. The generator uses Blender's built-in mesh, material and rendering tools. The delivered GLBs are self-contained. The verifier checks the profile, fixed shoulders, top, signed volume and topology using the actual exported triangles. [Geometry](reports/geometry.json) · [Native source](reports/source.json) · [Reproducibility and saved edit](reports/reproducibility.json) · [Rights](LICENSE.md)

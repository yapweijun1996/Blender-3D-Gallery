# Proton Saga (1985) — reference-led vehicle study

This draft is an original procedural Blender reconstruction of the first-generation sedan using the two user-provided exterior references. It has independently opening front and rear doors and a simplified period-inspired interior. The reference pictures do not show the original interior: trim, door hardware, hinge axes, proportions and materials are interpretations, not verified factory specifications or a dimensionally certified scan.

The gallery loads the GLB on demand and exposes four camera presets and four independent door toggles when all four `Door_*_Hinge` nodes are present. Reset closes the doors. If a pivot is absent, the viewer disables the door controls and keeps the model viewable. Front wheel steering and four wheel roll pivots also exist in the model, but the gallery does not provide wheel controls. The GLB has no animation clips; the viewer rotates the door nodes at runtime.

## Provenance and redistribution

The two files in `textures/` are the user-provided reference images. Pixels from them are used for the front and rear lamp textures; compressed full-image copies are embedded in the GLB. Rights to redistribute those images have not been independently verified. Download remains disabled and no third-party mesh is included. Proton and Saga identify the depicted vehicle and imply no endorsement.

The Blender studio scene uses the bundled Studio environment image, credited by Blender to Greg Zaal / Poly Haven under CC0. It is packed in `scene.blend` and does not ship in the GLB. The gallery viewer uses its own lighting, so browser appearance differs from Blender renders.

## Reproduction

`generate.py` generates `scene.blend`, `exports/proton-saga-1985.glb` and six exterior views. It requires Blender 5.1.2, the bundled images under `textures/`, `cwebp` at `/opt/homebrew/bin/cwebp`, and Blender's bundled Studio HDRI at the path specified in the script. From this directory:

```sh
/Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup --python-exit-code 1 --python generate.py
```

The default generator uses 48 Cycles samples. The checked-in updated exterior renders were generated from the final scene with 24 Cycles samples and denoising using `render_views.py`; `reports/render-report.json` records the scene hash and render settings. `-- --views none` builds source and GLB without rendering. The source uses Blender -X as front, -Y as left, +Z as up; the GLB root is `ASSET_Proton_Saga_1985`.

## Verification and limitations

The Blender scripts `verify_blend.py`, `verify_clearance.py`, `verify_hardware.py`, and `verify_hardware_pairs.py` check hierarchy and sampled door, adjacent-door, hardware and seal geometry. They do not establish continuous mechanical clearance, physical collision, exact manufacturing tolerances, or fidelity to a factory interior. `verify_gltf.mjs` and `reports/gltf-validation.json` record glTF validation. `reports/door-integration.json` records the current export hash and measured metrics; `reports/rebuild-verification.json` is historical evidence for the earlier exterior reconstruction, not the current GLB.

The gallery browser tests exercise actual model rendering, the four door controls, reset, view presets, missing-pivot fallback, keyboard and desktop/mobile viewport behavior. No physical device or real vehicle was tested. The model remains an artistic draft, not a 100% likeness claim.

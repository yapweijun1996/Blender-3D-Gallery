# Koi Fish

Original, brand-neutral P3 ornamental koi for an atrium pond, in the existing
**Fish** category and fish collection. No downloaded assets, images or fonts.
Analytic pearl, red and ink markings use vertex colours, with three shared opaque
materials and no textures. The editable source retains separate anatomical parts;
the exported weighted mesh has three material primitives.

The existing `fish-koi` was inspected before building. Both its current and legacy
files have cyclic swimming, but the current file has 77,182 triangles,
4,492,976 bytes and six materials; the legacy file has eight materials. They do
not meet this task's hard budgets. The explicit unsuitable-asset exception was
used to create this original small delivery; neither existing model was changed.
See `reports/duplicate-audit.json` for measured evidence and source paths.

Measured reference dimensions are 0.1120 x 0.0863 x 0.3004 m (width, height,
length). Source: metres, +Z up, -Y front. GLB: +Y up, +Z front, origin at the
floor centre of its reference-pose envelope. The root is `ASSET_KoiFish`.
Apply placement, rotation and scaling to the **whole loaded glTF scene**: the
skinned mesh is a scene-root sibling, as required by glTF skinning.

`Swim_Loop` spans 0–3 seconds, with cyclic body/tail yaw and pectoral fanning,
seven bones, at most three vertex influences and no root trajectory. The
actual exported tail moves up to 0.0421 m in the 25 sampled poses. Full sampled
motion bounds are in metadata and `reports/assets.json`. Place the fish inside
the water with clearance for the entire envelope; pond navigation and water
simulation belong to the consuming application. This is an artist-tuned visual
model, not a biological, engineering or animal-care specification.

Run from the repository root:

```sh
/opt/homebrew/bin/blender --background --python models/koi-fish/generate.py
/opt/homebrew/bin/blender --background --python models/koi-fish/inspect_sources.py
node models/koi-fish/validate.mjs --source-edit
npm run validate:assets
npm test
npm run build
node models/koi-fish/check_browser.mjs
```

Generation is deterministic with no random inputs. Rebuilding replaces saved
source edits. Preserve manual edits with `generate.py -- --export-source
--skip-render`. Source inspection reopens the saved file, modifies a tail copy
in memory, exports to `/tmp`, and does not save over the source.

The GLB contains 15,388 triangles, 7,734 stored vertices, 543,120 bytes, one
mesh definition, three primitives, three materials and one animation. The three
primitive nodes share one skeleton. Khronos, source, asset and runtime checks
are separate evidence. The overall status stays **NEEDS REVIEW** for manager
review. Physical devices, WebKit, continuous collision, an assembled pond and
full-mall performance remain unverified. No gallery UI or workflow changes.

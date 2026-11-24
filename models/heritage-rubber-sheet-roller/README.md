# Heritage Rubber Sheet Roller

An original still life of a hand-cranked workshop roller. It has an editable casting and wooden base, distinct smooth and longitudinally ribbed drums, a small side crank, exposed gear silhouettes and a single already-staged mock sheet with real embossed relief. The display does not operate.

Malaysia's [National Museum](https://www.muziumnegara.gov.my/en/rubber-sheets) documents the use of a textured roller in the historical context of rubber sheets. The museum is cited for that cultural context only. The scene is not a museum replica, equipment plan, operating instruction, processing or safety claim. All geometry and imagery are original; no booth, museum photo, label, machine drawing or external texture was used.

## Validate and reproduce

- Blender 4.3.2: `blender -b --factory-startup --threads 5 --python-exit-code 31 --python generate.py -- --output .`. Add `--review <dir>` for native front and rear details; `--skip-render` reproduces source and GLB only. An independent run of the same native command reproduced the exact exported GLB bytes.
- True roller profile, mock sheet topology and its clearance over each tray after GLB re-import: `blender -b --factory-startup heritage-rubber-sheet-roller.blend --python-exit-code 31 --python verify_blender.py -- exports/heritage-rubber-sheet-roller.glb`.
- From the repository root, `node models/heritage-rubber-sheet-roller/verify.mjs` validates exact named mesh profiles, Khronos conformance and SHA-256 digests.

Model units are illustrative metres, Blender +Z up and −Y outward, glTF +Y up and +Z outward. The poster is rendered from this source. Studio scenery and lighting are omitted from the export. Public download redistribution terms are not specified.

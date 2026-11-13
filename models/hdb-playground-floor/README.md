# HDB Playground Floor

V2.1 item 310. A modular four-metre rubber playground floor with sixteen editable tiles and eight high-contrast dot-count play cells.

Independent source `sources/hdb-playground-floor.blend`, generator `generate.py`, glTF `exports/optimized.glb`. All geometry/materials editable. Metres, Blender +Z up/front -Y; glTF +Y up/front +Z. Origin lower datum at 0. Studio excluded. No external models/textures/fonts.

Reproduce with Blender 4.0.2: --background --threads 2 --python-exit-code 1 --python models/hdb-playground-floor/generate.py. Append -- --export-source --skip-render to re-export saved source without rebuilding. node models/hdb-playground-floor/validate.mjs; Blender inspect_sources.py; node models/hdb-playground-floor/verify_source_edit.mjs. See verification.md for executed evidence.

No physical/safety/compliance claims. Source poses are not runtime interactivity. Owner-project reuse only, public redistribution unspecified.

# HDB Fitness Corner

V2.1 item 311. An outdoor fitness corner with independent parallel bars, a static waist-twist disc, handholds and a rubber exercise pad.

Independent source `sources/hdb-fitness-corner.blend`, generator `generate.py`, glTF `exports/optimized.glb`. All geometry/materials editable. Metres, Blender +Z up/front -Y; glTF +Y up/front +Z. Origin lower datum at 0. Studio excluded. No external models/textures/fonts.

Reproduce with Blender 4.0.2: --background --threads 2 --python-exit-code 1 --python models/hdb-fitness-corner/generate.py. Append -- --export-source --skip-render to re-export saved source without rebuilding. node models/hdb-fitness-corner/validate.mjs; Blender inspect_sources.py; node models/hdb-fitness-corner/verify_source_edit.mjs. See verification.md for executed evidence.

No physical/safety/compliance claims. Source poses are not runtime interactivity. Owner-project reuse only, public redistribution unspecified.

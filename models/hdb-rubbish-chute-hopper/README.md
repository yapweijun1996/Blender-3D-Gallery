# HDB Rubbish Chute Hopper

V2.1 item 314. A wall-mounted stainless rubbish-chute hopper with a separately editable lower hinge-pivot flap, pull handle and recessed housing.

Independent source `sources/hdb-rubbish-chute-hopper.blend`, generator `generate.py`, glTF `exports/optimized.glb`. All geometry/materials editable. Metres, Blender +Z up/front -Y; glTF +Y up/front +Z. Origin lower datum at 0. Studio excluded. No external models/textures/fonts.

Reproduce with Blender 4.0.2: --background --threads 2 --python-exit-code 1 --python models/hdb-rubbish-chute-hopper/generate.py. Append -- --export-source --skip-render to re-export saved source without rebuilding. node models/hdb-rubbish-chute-hopper/validate.mjs; Blender inspect_sources.py; node models/hdb-rubbish-chute-hopper/verify_source_edit.mjs. See verification.md for executed evidence.

No physical/safety/compliance claims. Source poses are not runtime interactivity. Owner-project reuse only, public redistribution unspecified.

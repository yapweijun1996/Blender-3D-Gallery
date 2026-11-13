# HDB Block Number Sign

V2.1 item 313. A deep-blue residential block sign with independently editable geometric placeholder numerals 123 and rear stand-off brackets.

Independent source `sources/hdb-block-number-sign.blend`, generator `generate.py`, glTF `exports/optimized.glb`. All geometry/materials editable. Metres, Blender +Z up/front -Y; glTF +Y up/front +Z. Origin lower datum at 0. Studio excluded. No external models/textures/fonts.

Reproduce with Blender 4.0.2: --background --threads 2 --python-exit-code 1 --python models/hdb-block-number-sign/generate.py. Append -- --export-source --skip-render to re-export saved source without rebuilding. node models/hdb-block-number-sign/validate.mjs; Blender inspect_sources.py; node models/hdb-block-number-sign/verify_source_edit.mjs. See verification.md for executed evidence.

No physical/safety/compliance claims. Source poses are not runtime interactivity. Owner-project reuse only, public redistribution unspecified.

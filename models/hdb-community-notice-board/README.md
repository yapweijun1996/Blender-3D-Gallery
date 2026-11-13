# HDB Community Notice Board

V2.1 item 312. A green community notice board with six independently replaceable abstract paper notices, original pictograms and two support posts.

Independent source `sources/hdb-community-notice-board.blend`, generator `generate.py`, glTF `exports/optimized.glb`. All geometry/materials editable. Metres, Blender +Z up/front -Y; glTF +Y up/front +Z. Origin lower datum at 0. Studio excluded. No external models/textures/fonts.

Reproduce with Blender 4.0.2: --background --threads 2 --python-exit-code 1 --python models/hdb-community-notice-board/generate.py. Append -- --export-source --skip-render to re-export saved source without rebuilding. node models/hdb-community-notice-board/validate.mjs; Blender inspect_sources.py; node models/hdb-community-notice-board/verify_source_edit.mjs. See verification.md for executed evidence.

No physical/safety/compliance claims. Source poses are not runtime interactivity. Owner-project reuse only, public redistribution unspecified.

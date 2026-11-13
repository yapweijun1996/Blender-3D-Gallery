# HDB Corridor Gate

V2.1 item 305. A charcoal open-grille residential corridor gate with independent hinge-pivot leaf, bronze accents, lever and hinge barrels.

Independent source: `sources/hdb-corridor-gate.blend`; reproducible generator: `generate.py`; optimized static glTF: `exports/optimized.glb`. Blender Z-up, glTF Y-up, metres. Source objects and materials remain individually editable. Studio camera/lights excluded from export.

Run Blender 4.0.2 `--background --threads 2 --python-exit-code 1 --python models/hdb-corridor-gate/generate.py`. Use `-- --export-source --skip-render` to export saved source without regenerating. Run `node models/hdb-corridor-gate/validate.mjs`, Blender `inspect_sources.py`, then `node models/hdb-corridor-gate/verify_source_edit.mjs`. See verification.md for actual evidence and coverage.

Illustrative visual module only. No structural, security, fire, electrical or accessibility compliance is asserted. No deployment performed.

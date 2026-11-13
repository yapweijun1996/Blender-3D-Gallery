# HDB Clothes Drying Rack

V2.1 item 307. An exterior wall-mounted drying rack with two cantilever brackets, diagonal braces, cross supports and six independently editable bamboo-coloured poles.

Independent source: `sources/hdb-clothes-drying-rack.blend`; reproducible generator: `generate.py`; optimized static glTF: `exports/optimized.glb`. Blender Z-up, glTF Y-up, metres. Source objects and materials remain individually editable. Studio camera/lights excluded from export.

Run Blender 4.0.2 `--background --threads 2 --python-exit-code 1 --python models/hdb-clothes-drying-rack/generate.py`. Use `-- --export-source --skip-render` to export saved source without regenerating. Run `node models/hdb-clothes-drying-rack/validate.mjs`, Blender `inspect_sources.py`, then `node models/hdb-clothes-drying-rack/verify_source_edit.mjs`. See verification.md for actual evidence and coverage.

Illustrative visual module only. No structural, security, fire, electrical or accessibility compliance is asserted. No deployment performed.

Mounting datum: lower wall-plate edge, wall plane Y=0, poles extend -Y. Generic geometry only, no load rating or installation specification.

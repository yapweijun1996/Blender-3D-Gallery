# HDB Bicycle Parking Shelter

V2.1 item 309. A four-post covered bicycle-parking bay with a shallow pitched opaque metal roof, footing pads and four independent inverted-U cycle stands.

Independent source: `sources/hdb-bicycle-parking-shelter.blend`; reproducible generator: `generate.py`; optimized static glTF: `exports/optimized.glb`. Blender Z-up, glTF Y-up, metres. Source objects and materials remain individually editable. Studio camera/lights excluded from export.

Run Blender 4.0.2 `--background --threads 2 --python-exit-code 1 --python models/hdb-bicycle-parking-shelter/generate.py`. Use `-- --export-source --skip-render` to export saved source without regenerating. Run `node models/hdb-bicycle-parking-shelter/validate.mjs`, Blender `inspect_sources.py`, then `node models/hdb-bicycle-parking-shelter/verify_source_edit.mjs`. See verification.md for actual evidence and coverage.

Illustrative visual module only. No structural, security, fire, electrical or accessibility compliance is asserted. No deployment performed.

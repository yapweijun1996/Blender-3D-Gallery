# HDB Utility Riser

V2.1 item 306. A cream double-door utility-riser enclosure with modeled louver fins, recessed vent backing, locks and a blank replaceable identifier plate.

Independent source: `sources/hdb-utility-riser.blend`; reproducible generator: `generate.py`; optimized static glTF: `exports/optimized.glb`. Blender Z-up, glTF Y-up, metres. Source objects and materials remain individually editable. Studio camera/lights excluded from export.

Run Blender 4.0.2 `--background --threads 2 --python-exit-code 1 --python models/hdb-utility-riser/generate.py`. Use `-- --export-source --skip-render` to export saved source without regenerating. Run `node models/hdb-utility-riser/validate.mjs`, Blender `inspect_sources.py`, then `node models/hdb-utility-riser/verify_source_edit.mjs`. See verification.md for actual evidence and coverage.

Illustrative visual module only. No structural, security, fire, electrical or accessibility compliance is asserted. No deployment performed.

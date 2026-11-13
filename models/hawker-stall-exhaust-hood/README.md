# Hawker Stall Exhaust Hood

V2.1 item 362. A compact stainless hawker exhaust canopy with a sloped fascia, four removable underside baffle filters and an upper duct stub.

Independent editable source `sources/hawker-stall-exhaust-hood.blend`, generator `generate.py`, glTF `exports/optimized.glb`. Metres, Blender +Z up/front -Y; glTF +Y up/front +Z. Source components and materials remain independent; no runtime operation claimed.

Reproduce with Blender 4.0.2 `--background --threads 2 --python-exit-code 1 --python models/hawker-stall-exhaust-hood/generate.py`. Append `-- --export-source --skip-render` to export saved source without regeneration. Run `node models/hawker-stall-exhaust-hood/validate.mjs`, Blender `inspect_sources.py`, then `node models/hawker-stall-exhaust-hood/verify_source_edit.mjs`. Source inspection writes report/edited-fixture files; run an isolated copy to preserve prior evidence. See verification.md for actual checks and limits.

Generic original design, not certified building/service equipment. No deployment or public redistribution license.

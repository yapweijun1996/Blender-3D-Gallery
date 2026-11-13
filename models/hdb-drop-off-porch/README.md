# HDB Drop-Off Porch

V2.1 item 320. An open-sided residential drop-off canopy with a rear walkway, two independent columns, a shallow ramp, teal fascia and underside light housings.

Independent editable source `sources/hdb-drop-off-porch.blend`, generator `generate.py`, glTF `exports/optimized.glb`. Metres, Blender +Z up/front -Y; glTF +Y up/front +Z. Source components and materials remain independent; no runtime operation claimed.

Reproduce with Blender 4.0.2 `--background --threads 2 --python-exit-code 1 --python models/hdb-drop-off-porch/generate.py`. Append `-- --export-source --skip-render` to export saved source without regeneration. Run `node models/hdb-drop-off-porch/validate.mjs`, Blender `inspect_sources.py`, then `node models/hdb-drop-off-porch/verify_source_edit.mjs`. Source inspection writes report/edited-fixture files; run an isolated copy to preserve prior evidence. See verification.md for actual checks and limits.

Generic original design, not certified building/service equipment. No deployment or public redistribution license.

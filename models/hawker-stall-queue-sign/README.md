# Hawker Stall Queue Sign

V2.1 item 364. A teal freestanding hawker queue marker with editable QUEUE HERE lettering, a separate right-pointing arrow and weighted circular base.

Independent editable source `sources/hawker-stall-queue-sign.blend`, generator `generate.py`, glTF `exports/optimized.glb`. Metres, Blender +Z up/front -Y; glTF +Y up/front +Z. Source components and materials remain independent; no runtime operation claimed.

Reproduce with Blender 4.0.2 `--background --threads 2 --python-exit-code 1 --python models/hawker-stall-queue-sign/generate.py`. Append `-- --export-source --skip-render` to export saved source without regeneration. Run `node models/hawker-stall-queue-sign/validate.mjs`, Blender `inspect_sources.py`, then `node models/hawker-stall-queue-sign/verify_source_edit.mjs`. Source inspection writes report/edited-fixture files; run an isolated copy to preserve prior evidence. See verification.md for actual checks and limits.

Generic original design, not certified building/service equipment. No deployment or public redistribution license.

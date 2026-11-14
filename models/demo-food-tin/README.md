# Demo Food Tin

Original unbranded packaging concept, not a real food product or engineering specification.

Run `python3 models/demo-food-tin/label.py`, then Blender background with `--threads 2 --python models/demo-food-tin/generate.py`. Node `models/demo-food-tin/validate.mjs` writes the structural/raw-motion report. Blender `--python models/demo-food-tin/source-proof.py` makes and reopens an edited copy, does not regenerate it.

Two mutually exclusive 3-second clips: OpenClose and Exploded. Times 0 and 3 are rest; 1.5 is open/exploded. Stop/reset current clip before changing. Source NLA tracks intentionally muted to avoid combining clips; enable the single matching track on each animated object to inspect. Export helper enables both named tracks for distinct glTF clips.

Source, structural, 121-sample-per-clip, studio visual and Chromium browser gates PASS. Current evidence: docs/product-studio/evidence/canvas-fix-final. Physical Android/iOS/Safari NOT TESTED. CI and deployment status are tracked separately.

Seven independently editable mesh primitives, metric real dimensions, packed texture, UV seam at rear. Body is a manifold hollow shell with solid bottom; label is intentionally a single-sided wrap. Lid has a deliberate clearance and removable motion, not tearing or sealing physics. Ring-rivet attachment is intentional; ring/lid clearance is a visual illustration, not a manufacturing tolerance.

Preserved evidence: initial renderer failure (OpenImageDenoiser unavailable), initial bright studio source/export/previews, and initial validator constant STEP-track diagnostic. Constant tracks are only accepted after asserting all values equal; motion tracks retain LINEAR requirement. No budget or geometric assertion relaxed.

Original artwork uses DejaVu Sans; license retained. Public redistribution terms for the model not specified, downloads disabled.

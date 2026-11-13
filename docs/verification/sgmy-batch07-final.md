# SG/MY batch 07 · Cendol cart and transport modules380–389

**Ten new independent types. Every local asset PASS; every overall result NEEDS REVIEW because physical Android/iOS is NOT TESTED.** This is review evidence, not deployment approval.

Integrated additively on current main `2d8f7731fc7f9a01b77172780f3e31aa54228ad3`. No unmerged asset batches or unreviewed Solar repair imported. No source architecture/schema changes, main merge or deployment performed.

| ID | Asset | GLB bytes | Local source / geometry / visual / strict viewer | Overall |
| --- | --- | ---: | --- | --- |
| 380 | [Cendol Dessert Cart](../../models/cendol-dessert-cart/verification.md) | 337,692 | PASS; 3/3 viewports | NEEDS REVIEW |
| 381 | [Singapore Traffic Signal Pole](../../models/singapore-traffic-signal-pole/verification.md) | 151,980 | PASS; 3/3 viewports | NEEDS REVIEW |
| 382 | [Malaysia Traffic Signal Pole](../../models/malaysia-traffic-signal-pole/verification.md) | 157,076 | PASS; 3/3 viewports | NEEDS REVIEW |
| 383 | [Singapore ERP Gantry Concept](../../models/singapore-erp-gantry-concept/verification.md) | 153,756 | PASS; 3/3 viewports | NEEDS REVIEW |
| 384 | [Malaysia Toll Plaza Canopy](../../models/malaysia-toll-plaza-canopy/verification.md) | 130,920 | PASS; 3/3 viewports | NEEDS REVIEW |
| 385 | [Malaysia Touch 'n Go Lane Sign](../../models/malaysia-card-lane-sign/verification.md) | 39,096 | PASS; 3/3 viewports | NEEDS REVIEW |
| 386 | [Road Direction Gantry](../../models/road-direction-gantry/verification.md) | 144,684 | PASS; 3/3 viewports | NEEDS REVIEW |
| 387 | [Motorcycle Parking Bay](../../models/motorcycle-parking-bay/verification.md) | 140,804 | PASS; 3/3 viewports | NEEDS REVIEW |
| 388 | [HDB Car Park Ramp](../../models/hdb-car-park-ramp/verification.md) | 16,984 | PASS; 3/3 viewports | NEEDS REVIEW |
| 389 | [Covered Motorcycle Parking](../../models/covered-motorcycle-parking/verification.md) | 101,648 | PASS; 3/3 viewports | NEEDS REVIEW |

## Final gates

- [235/235 units](sgmy-batch07-final/final-unit.log), no skips; [build/catalog/Khronos validation PASS](sgmy-batch07-final/final-build.log), rerun after final preview/metadata edits.
- Strict **30/30 browser cases PASS** in one fixed combined pass: [380–384 /15](sgmy-batch07-final/browser-b/results.json), [385](sgmy-batch07-final/browser-malaysia-card-lane-sign/results.json), [386](sgmy-batch07-final/browser-road-direction-gantry/results.json), [387](sgmy-batch07-final/browser-motorcycle-parking-bay/results.json), [388](sgmy-batch07-final/browser-hdb-car-park-ramp/results.json), [389](sgmy-batch07-final/browser-covered-motorcycle-parking/results.json). Tests check exact consumed bytes/SHA, HTTP200, actual drawing, orbit/zoom/reset/reopen, repeated lifecycle, stopped rendering/focus return, disabled downloads, no overflow and unfiltered unexpected request/console/page errors.
- [Loading lifecycle4/4](sgmy-batch07-final/lifecycle/results.json), [library9/9](sgmy-batch07-final/library/results.json) PASS. This does not establish a repair for unrelated failures observed in other batches.
- Independent all ten source inspections, geometry validators and real source-edit validators PASS; all ten saved edited .blend files independently reopened and reexported byte-identical GLBs. [Source evidence](sgmy-batch07-final/independent-review/). Original delivered sources/reports remained unchanged; tests used isolated copies.
- All ten multi-angle studio sets inspected, including corrected389primary. All30 final Gallery initial images independently inspected; [independent review PASS](sgmy-batch07-final/independent-review/independent-review.json); [contact sheet](sgmy-batch07-final/final-browser-contact.webp).
- [Old-default regression](sgmy-batch07-final/legacy-preview-comparison.json): main baseline14/14 and candidate14/14, all **70 initial/orbit/zoom/reset/reopened image hashes unchanged**. Optional per-model preview configuration changes only the new assets. No ceiling-must-change comparison from the old PR12 harness is applied.
- [Preservation](sgmy-batch07-final/preservation.json):100 previous catalog assets unchanged,110total, no duplicate registration; only catalog differs among old tracked files.405 producer report/evidence files byte-identical. Ten GLBs total **1,374,640 bytes**. Existing models, rights and test evidence are retained.

## Retained development evidence

- Traffic poles381/382 and canopy384 received approved per-model view settings during visual preflight before producer strict acceptance; original/final preflight images remain. Settings use existing optional fields, not new schema or global defaults.
- Motorcycle bay387 initially had an incorrect validator assumption equating total width with slab width. Final precise assertions require3.175m overall and3.1m slab, not a loosened tolerance. Initial validator/refinement failures remain; final geometry includes engine/saddle details in the motorcycle pictogram.
- Covered parking389 initially had a white roof blending into its light studio background. Review caught this despite correct GLB rendering. Only studio-floor background and three rendered PNG/WebP pairs were refined; original images/logs are preserved. Independent review accepted the corrected contrast. Source geometry and GLB bytes are unchanged, so the strict viewer evidence still covers the exact delivered GLB. Unit/build checks were repeated after this preview-only refinement.
- Historical pending statements and initial failures remain chronological evidence; final metadata points to this combined gate. Copied generator comment headers were clarified to actual asset names without changing generation logic.

## Asset distinctions and limits

Each asset has independent Blender Python, editable `.blend`, optimized `.glb`, multi-angle previews, metadata, rights/provenance and validation reports. Cendol cart is distinct from the prior general retail cart. Singapore/Malaysia signal poles differ in geometry, heights, footings, button versus maintenance-door details and bands, not only color. They are generic region-inspired visual interpretations, not authoritative road-control standards.

ERP gantry383 is explicitly a concept, not a deployed system replica. Illustrative measured clear widths are8.05m for383 and two3.85m lanes for384; layout checks are not structural, traffic, accessibility, installation or clearance certification.385 uses an original nonproprietary card/arrow pictogram. Signs, arrows, lanes and emissions are static; no toll payment, traffic-control logic, road safety guidance or runtime operation is implemented.

All ten stay within their documented complexity-specific budgets. Bundled font/context attribution and owner-project reuse rights remain; no unspecified public redistribution license invented. Public downloads stay disabled, and reused components/context do not increase logical model counts.

Actual environment: Ubuntu ARM64, desktop Chromium156.0.8078.4 / SwiftShader;1440×900,768×1024,390×844 viewport emulation. **Physical Android/iOS, native mobile GPU/touch behavior and Safari/WebKit are NOT TESTED.** The library harness has inherited macOS wording, not the actual runner. Every overall result stays NEEDS REVIEW. Pages build success does not replace comprehensive or real-device acceptance; no unverified deployment is authorized.

Authored source/tests/metadata/docs pass whitespace checks. Raw build/test log whitespace is preserved as evidence.

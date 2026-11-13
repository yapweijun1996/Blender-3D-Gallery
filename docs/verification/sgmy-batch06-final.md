# SG/MY batch 06 · Kopitiam and mamak assets370–379

**Ten new independent logical assets. Each local asset PASS; each overall NEEDS REVIEW because physical Android/iOS is NOT TESTED.** This is a draft-review candidate, not deployment approval.

Fresh main base `2d8f7731fc7f9a01b77172780f3e31aa54228ad3`. Added only these ten assets, their tests/evidence and catalog registrations. No unmerged model batches or unreviewed Solar repair were imported. No branch merge, remote publication, main merge or deployment performed by assembly.

| ID | Asset | GLB bytes | Local source / geometry / visual / strict viewer | Overall |
| --- | --- | ---: | --- | --- |
| 370 | [Kopitiam Kettle](../../models/kopitiam-kettle/verification.md) | 152,424 | PASS; 3/3 viewports | NEEDS REVIEW |
| 371 | [Kopitiam Saucer and Cup](../../models/kopitiam-saucer-and-cup/verification.md) | 133,956 | PASS; 3/3 viewports | NEEDS REVIEW |
| 372 | [Kopitiam Condiment Tray](../../models/kopitiam-condiment-tray/verification.md) | 174,708 | PASS; 3/3 viewports | NEEDS REVIEW |
| 373 | [Kopitiam Toast Display](../../models/kopitiam-toast-display/verification.md) | 222,880 | PASS; 3/3 viewports | NEEDS REVIEW |
| 374 | [Mamak Roti Canai Griddle](../../models/mamak-roti-canai-griddle/verification.md) | 159,808 | PASS; 3/3 viewports | NEEDS REVIEW |
| 375 | [Mamak Teh Tarik Jug](../../models/mamak-teh-tarik-jug/verification.md) | 83,840 | PASS; 3/3 viewports | NEEDS REVIEW |
| 376 | [Mamak Curry Pot](../../models/mamak-curry-pot/verification.md) | 161,268 | PASS; 3/3 viewports | NEEDS REVIEW |
| 377 | [Mamak Stainless Steel Plate](../../models/mamak-stainless-steel-plate/verification.md) | 100,036 | PASS; 3/3 viewports | NEEDS REVIEW |
| 378 | [Mamak Wall Menu Board](../../models/mamak-wall-menu-board/verification.md) | 75,624 | PASS; 3/3 viewports | NEEDS REVIEW |
| 379 | [Satay Skewer Display](../../models/satay-skewer-display/verification.md) | 302,684 | PASS; 3/3 viewports | NEEDS REVIEW |

## Final combined acceptance evidence

- [235/235 units](sgmy-batch06-final/final-unit.log), no skips; [build/catalog/Khronos validation PASS](sgmy-batch06-final/final-build.log). All ten assets stay within their documented polygon and file-size budgets.
- Strict **30/30 browser cases PASS** in one fixed combined gate: [370–374 /15](sgmy-batch06-final/browser-b/results.json), [375](sgmy-batch06-final/browser-mamak-teh-tarik-jug/results.json), [376](sgmy-batch06-final/browser-mamak-curry-pot/results.json), [377](sgmy-batch06-final/browser-mamak-stainless-steel-plate/results.json), [378](sgmy-batch06-final/browser-mamak-wall-menu-board/results.json), [379](sgmy-batch06-final/browser-satay-skewer-display/results.json). Exact consumed GLB bytes/SHA, HTTP200, real drawing, orbit/zoom/reset/reopen, repeated lifecycle, stopped rendering/focus return, disabled downloads and no overflow; all unexpected request/console/page errors are unfiltered.
- [Lifecycle4/4](sgmy-batch06-final/lifecycle/results.json) and [library9/9](sgmy-batch06-final/library/results.json) PASS. This is batch06 evidence only, not a claim that unrelated earlier library failures were fixed.
- Independent **ten delivered source reopens, ten geometry validators, ten actual source-edit validators PASS**. Additionally [all ten edited saved .blend files reopened and reexported byte-identical GLBs](sgmy-batch06-final/independent-review/full/reopened-edit-proof.json). See [full source evidence](sgmy-batch06-final/independent-review/full/) and [source reopen checks](sgmy-batch06-final/independent-review/reopen.json). Tests ran in isolated copies; producer reports and delivered sources stayed unchanged.
- All ten multi-angle studio preview sets and all30 final Gallery initial screenshots independently inspected; [final independent review PASS](sgmy-batch06-final/independent-review/independent-review.json). [Final contact sheet](sgmy-batch06-final/final-browser-contact.webp). Actual pixel review, not merely test assertions, determined the metal presentation refinements below.
- [Old-default comparison](sgmy-batch06-final/legacy-preview-comparison.json): baseline14/14 and candidate14/14, **70/70 exact unchanged initial/orbit/zoom/reset/reopened image hashes** across seven existing types and two widths. Existing models retain their defaults. The original preview harness runs without its historical ceiling-must-change argument; the separate comparison correctly requires all old models unchanged.
- [Preservation](sgmy-batch06-final/preservation.json): all100 previous catalog entries unchanged,110 total, no duplicate IDs; only catalog changed among old tracked files.442 producer historical report/evidence files byte-identical. Ten delivered GLBs total **1,567,228 bytes**. Previously delivered assets and evidence are untouched.

## Refinement chronology and retained failures

- Condiment tray372 initially exceeded its fixed5000triangle budget at5204. The failure remains in its `reports/initial-over-budget` evidence; geometry was optimized to3636triangles without raising the budget or weakening validation.
- Initial strict30 assertions passed, but actual pixel inspection found kettle370, griddle374 and plate377 too dark. Existing approved optional per-model preview lighting was adjusted only for these types. Producer affected-case follow-ups passed6/6 for370/374 and3/3 for377, and the final combined30/30 above uses corrected metadata. No geometry, schema, global defaults or app behavior changed. Initial screenshots/results remain preserved.
- Generator comment headers copied from an earlier model were corrected to the actual asset names; no generation logic changed. Metadata pending statements were updated to reference this combined result; historical reports are left at their original chronological status.

## Scope, rights and platform limits

Each independent asset has Blender Python source, editable `.blend`, optimized `.glb`, multi-angle previews, metadata, provenance/rights and test evidence. Kettle spout, cup interior, jug mouth, pot lid/body and plate rim/bowl are actual editable geometry. Source labels and individual components remain independently editable. The pot lid-raised preview is a source-only pose, not runtime animation. Reused context tray439 and grouped cup/saucer/condiments do not inflate the ten logical-type count.

Original asset rights and bundled Bfont/context attribution are retained. Owner-project reuse does not establish unspecified public redistribution rights. Public downloads remain disabled. These are static illustrative props, not food-contact, hygiene, electrical, heating, fabrication or safety-certified products, and not fluid/heat/cloth simulation or runtime machinery.

Actual runner: Ubuntu ARM64, desktop Chromium156.0.8078.4 / SwiftShader;1440×900,768×1024,390×844 viewport emulation. **Physical Android/iOS, native mobile GPU/touch behavior and Safari/WebKit are NOT TESTED.** The raw library harness retains inherited macOS wording; it does not describe the actual runner. Each overall asset remains NEEDS REVIEW. Successful Pages builds do not substitute for comprehensive gates or real-device acceptance; no unverified deployment is authorized.

Authored source/tests/metadata/documentation pass whitespace checks. Raw build/test log whitespace is preserved as evidence rather than sanitized.

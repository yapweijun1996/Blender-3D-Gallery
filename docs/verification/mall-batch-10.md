# Mall batch: independent final verification

**Local review: PASS. Overall: NEEDS REVIEW for every type.** Actual Android and iOS are **NOT TESTED**. Desktop viewport emulation is not physical-device, touch, mobile GPU or production-performance acceptance. This report does not assert a push, PR, merge, deployment or release.

Reviewed implementation: `955bca52d7ca7cbeb5a053b37de0e0e8312c6bd1`, compared with main baseline `b7421d284b503ff923508fc3046b2193108f503a`. Review ran on 2026-11-12 in a fresh isolated clone, with no implementation or test changes. The subsequent reconciliation adds only evidence and status documentation/metadata; original reports, including failures, are retained.

## Count and gates

Exactly **10 logical types and 12 GLB files**: retained 006 counts once despite its three variants; 421–429 each count once. Included floor/railing context in assemblies does not add models. 429 is a landing module; full escalator is 004, while 430 is the separate handrail.

| V2.1 ID | Type | GLBs | Strict browser cases | Local asset gate | Overall / platform gate |
| --- | --- | ---: | ---: | --- | --- |
| 006 | [Glass railing kit (retained)](../../models/mall-glass-railing/README.md) | 3 | 9/9 | PASS | NEEDS REVIEW |
| 421 | [Floor tile](../../models/mall-floor-tile/README.md) | 1 | 3/3 | PASS | NEEDS REVIEW |
| 422 | [Ceiling panel](../../models/mall-ceiling-panel/README.md) | 1 | 3/3 | PASS | NEEDS REVIEW |
| 423 | [Ceiling light](../../models/mall-ceiling-light/README.md) | 1 | 3/3 | PASS | NEEDS REVIEW |
| 424 | [Shopfront door](../../models/mall-shopfront-door/README.md) | 1 | 3/3 | PASS | NEEDS REVIEW |
| 425 | [Roller shutter](../../models/mall-shopfront-roller-shutter/README.md) | 1 | 3/3 | PASS | NEEDS REVIEW |
| 426 | [Glass partition](../../models/mall-glass-partition/README.md) | 1 | 3/3 | PASS | NEEDS REVIEW |
| 427 | [Structural column](../../models/mall-structural-column/README.md) | 1 | 3/3 | PASS | NEEDS REVIEW |
| 428 | [Atrium balcony](../../models/mall-atrium-balcony/README.md) | 1 | 3/3 | PASS | NEEDS REVIEW |
| 429 | [Escalator landing](../../models/mall-escalator-landing/README.md) | 1 | 3/3 | PASS | NEEDS REVIEW |

Every type passed its real-GLB validator and saved-source reopening. Browser cases use 1440×900, 768×1024 and 390×844 viewports. Full metrics, source/export SHA-256 values, rights and per-check exit codes are in the [verification manifest](mall-batch-10/verification.json).

## Independently executed checks

- **165/165 unit tests**, no failures or skips: [log](mall-batch-10/unit.log).
- **Build and catalog GLB validation PASS**: [log](mall-batch-10/build.log). Existing >500 kB shared-JavaScript chunk warning remains. No configured lint or typecheck script exists.
- **36/36 strict browser cases** over 12 actual GLBs, without filtering unexpected request failures, console errors, page errors or HTTP errors. Consumed byte lengths/hashes match the shipped GLBs; WebGL draws, orbit/zoom/reset, disabled downloads and no horizontal overflow are checked. The newer asset suites additionally require exact reset/reopen images; the unchanged railing/floor suites retain their original interaction assertions.
- **Loading lifecycle 4/4**: [results](mall-batch-10/lifecycle.json). Real partial-transfer cancellation, reopen, and HTTP/truncation/transport failure recovery. Only deliberately injected failures are expected.
- **Library 9/9**: [results](mall-batch-10/library.json), including navigation/history, lazy loading, repeated opening and resource release. The inherited `macOS` label inside this raw report is historical harness wording; actual execution was Ubuntu Linux ARM64.
- **Preview baseline 14/14 and candidate 14/14**: independently built ancestor `7a69dd674d5b3ad10739187e01a4f5a491c2cde8`, then ran exact comparisons with the final candidate. [Baseline](mall-batch-10/preview-baseline.json), [candidate](mall-batch-10/preview-candidate.json). Pool table, Ball 08, Earth, Saga, floor and railing retain identical initial/orbit/zoom/reset PNG hashes at both widths. Ceiling changes intentionally; configured reset/reopen remains exact. The pre-existing narrow Saga initial/reset fit difference is retained, not repaired or concealed.
- **10 source-inspection scripts reopened all 12 delivered .blend files** with Blender 4.0.2. Fresh isolated mesh/material edits and re-export also passed for [428](mall-batch-10/verify-edit-atrium-balcony.log) and [429](mall-batch-10/verify-edit-escalator-landing.log), preserving unrelated geometry/materials and shipped sources.
- **Four glass diagnostics PASS**: [railing](mall-batch-10/glass-railing.json), [door](mall-batch-10/glass-door.json), [partition](mall-batch-10/glass-partition.json), [balcony](mall-batch-10/glass-atrium.json). These compare original alpha glass against opaque/hidden controls, not physical refraction.
- Actual final 390 px initial canvases were independently inspected: [006–424](mall-batch-10/contact-1.jpg), [425–429](mall-batch-10/contact-2.jpg). No obvious clipping or missing model was found. Nine earlier primary studio previews and the landing source/assembly evidence were also reviewed. This is local visual review, not device certification.

Environment: Ubuntu Linux ARM64, Node 22.23.3, Blender 4.0.2, Playwright 1.64.1, Chromium 156.0.8078.4 / SwiftShader. Tests ran sequentially with isolated output paths and ephemeral loopback ports. All application checks passed on the first combined run. An initial **report-assembly** assertion incorrectly assumed build output count equaled catalog count; its [correction](mall-batch-10/report-assembly-initial.txt) is retained. No test was weakened or rerun to conceal a failure.

## Preservation, scope and budgets

- All **68 pre-existing catalog entries are unchanged**, with no removed/duplicate IDs. Final catalog has 80 entries. No pre-existing model source/export was modified. All metadata paths exist and thumbnails decode.
- All **96 built GLBs match repository source bytes**: 80 catalog assets plus 16 existing Solar/NASA demo assets. Those extra demo files are not new mall registrations. All 12 batch GLB hashes and source hashes match recorded metadata/evidence.
- Batch maxima: **486,156 bytes**, **4,940 triangles**, **32,444-byte served thumbnail**, texture dimensions at most **512×512**. PNG render masters are archival, not card payloads. No batch GLB requires external resource URLs or compression decoders.
- Runtime diff is limited to the separately approved optional per-model preview camera/light metadata and evidence-backed native-fetch GLB transport fix. Omitted settings preserve old defaults. No UI redesign, Game/Solar architecture change or unrelated source modification was found.
- Original source files, generators, reproduction instructions and rights statements are present. Owner-project reuse remains authorized; public redistribution terms remain unspecified and public downloads remain disabled. No new license or permission was invented.
- These are visual assets, not engineering, safety or building-code specifications. The Gallery exposes static viewing controls, not functional door/shutter controls, motorized transport or light switches. Emissive light material does not illuminate neighboring Gallery geometry. Full-escalator compatibility for 429 remains **NOT TESTED**.

## Current results supersede historical limitations only within this scope

- 006's initial strict request-abort failure remains in [its historical report](../../models/mall-glass-railing/verification.md) and original JSON. The [transport diagnosis/fix](../gallery-loading.md) and this fresh [9/9 run](mall-batch-10/browser-glass-railing.json) supersede the claim that its browser failure is still unresolved. Overall remains NEEDS REVIEW.
- 422's original rear/dark-underside observations remain in [its report](../../models/mall-ceiling-panel/verification.md). [Approved preview configuration](preview-config.md) and this [3/3 run](mall-batch-10/browser-ceiling-panel.json) verify the corrected initial underside view without source/GLB changes.
- 423's original rear/dark-frame observations remain in [its report](../../models/mall-ceiling-light/verification.md). [Approved preview integration](../../models/mall-ceiling-light/preview-config-verification.md) and this [3/3 run](mall-batch-10/browser-ceiling-light.json) supersede those presentation limitations. Native-device and photometric limits remain.

After the status reconciliation, full [unit tests](mall-batch-10/post-reconciliation-unit.log) again passed **165/165**, and [build/asset validation](mall-batch-10/post-reconciliation-build.log) passed. No runtime, geometry, catalog registration or test code changed.

## Reproduce

Use locked dependencies, Blender 4.0.2 and fresh output directories. From the repository root:

```sh
npm ci
npm test
npm run build
for m in glass-railing floor-tile ceiling-panel ceiling-light shopfront-door shopfront-roller-shutter glass-partition structural-column atrium-balcony escalator-landing; do
  node "models/mall-$m/validate.mjs"
  blender --background --threads 2 --python-exit-code 1 --python "models/mall-$m/inspect_sources.py"
  MALL_QA_DIR="/fresh/review/$m" node "scripts/test-mall-$m.mjs"
done
TEST_ARTIFACT_DIR=/fresh/review/lifecycle node scripts/test-gallery-loading.mjs
TEST_ARTIFACT_DIR=/fresh/review/library npm run test:library
# Build ancestor 7a69dd6 in a separate checkout, preserving its dist directory.
node scripts/test-preview-config.mjs /path/to/baseline/dist /fresh/review/preview-baseline
node scripts/test-preview-config.mjs dist /fresh/review/preview-candidate /fresh/review/preview-baseline
```

Per-asset READMEs document source-edit and glass-diagnostic invocations. Trailing whitespace emitted by Vite was removed only from copied build logs; raw local logs remain intact. Full screenshot sets and isolated edited-source fixtures were retained locally; compact machine-readable results, logs and representative pixels are committed here.

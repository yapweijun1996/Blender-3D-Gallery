# Fourth batch of 50 assets

**Local integration: PASS. Release status: NEEDS REVIEW.**

Tested base: `9604912f6eded65d01424e6ff229f15fd739077d`.

This batch adds 50 independent assets. All 244 prior catalog entries and tracked files are preserved, for 294 total entries. There is no overlap with the separate third batch of 50.

## Results

One fixed integration pass completed without retries or runtime changes:

- 366 unit tests and the build passed.
- All 9 library cases and 4 lifecycle cases passed.
- All 150 new viewport cases passed.
- All 9 isolated browser animation cases passed: 5 retail and 4 care/hotel assets.
- All 14 legacy preview cases passed.
- Pre-test and post-test preservation checks passed.

This result does **not** resolve the separate third batch's failed library regression in PR #21.

## Evidence

- `summary.json`: per-asset final source/GLB hashes, counts and limitations.
- `import-*.json`: exact producer commits and imported paths.
- `integration/status.tsv`: fixed-pass command results, with detailed logs and screenshots alongside it.
- `pixel-comparison.json`: all 150 final GLB hashes and initial screenshot hashes exactly match the producers' final reviewed cases.
- `fresh-contact-0.jpg` through `fresh-contact-4.jpg`: 50 fresh desktop screenshots actually inspected. All assets were recognizable and framed without a new visible defect.
- `files.txt`: complete batch file manifest.

Source-edit, GLB and multi-angle evidence is preserved unchanged from the committed producers. Exact matching pixels carry forward the prior matched-view inspection evidence; they do not establish physical-device compatibility.

The independent GitHub clone was created after a shared clone exceeded Git's alternate-object nesting limit before checkout. The partial clone was retained outside this repository. No upstream repository or security settings were changed.

## Limitations

- Physical Android/iOS and shipping Safari/WebKit remain unverified for these 50 assets.
- The 10 animated domestic assets have GLB/source proof and inspected Blender opening poses. They are **not** included in the 9 fresh isolated browser animation cases.
- No Gallery component-playback UI was added.
- Metadata remains draft. There is no engineering, medical or safety certification.
- No production deployment or remote publication was performed by this integration worker.
- The library report retains an inaccurate inherited “macOS” label. Actual integration ran on Ubuntu Chromium with SwiftShader.

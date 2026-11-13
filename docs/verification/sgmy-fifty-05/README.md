# Fifth batch of 50 assets

**Local integration: PASS. Release status: NEEDS REVIEW.**

Tested base: c5599b17891fc97da57295782305bdae5d7a8511, also confirmed as main after the final gate.

This batch adds 50 independent assets. All 294 prior catalog entries and tracked files are preserved, for 344 total entries. There is no overlap with the separate third batch, and the merged fourth batch remains unchanged.

## Results

One fixed integration pass on the current runtime completed:

- 404 unit tests and the build passed.
- All 9 library cases and 4 lifecycle cases passed.
- All 150 new viewport cases passed.
- All 7 isolated browser animation cases passed: 4 transport and 3 city-shell assets.
- All 14 legacy preview cases passed.
- Pre-test and post-test preservation checks passed.

The completed earlier d9 baseline pass is preserved under prior-d9. A fresh independent clone was tested because main subsequently changed shared viewer/catalog code. No assertions were weakened, no assets regenerated, and no merge or rebase was performed. These passes do not resolve the separate third batch's failed library regression in PR #21.

## Evidence

- summary.json records per-asset final source/GLB hashes, counts and limitations.
- import-*.json identifies exact producer commits and imported paths.
- integration/status.tsv and detailed logs preserve the fixed-pass results.
- pixel-comparison.json proves all 150 final GLB hashes and initial screenshot hashes match the producers' final reviewed cases.
- fresh-contact-0.jpg through fresh-contact-4.jpg contain 50 fresh desktop screenshots actually inspected. Assets are recognizable and framed without a new visible defect.
- files.txt is the complete changed-file manifest.

Source-edit, GLB and multi-angle evidence is preserved unchanged from committed producers. Exact pixel comparisons carry forward matched-view inspection evidence; they do not establish physical-device compatibility.

## Limitations

- Physical Android/iOS and shipping Safari/WebKit remain unverified for these 50 assets.
- The workplace tranche has seven inspected Blender action poses and GLB/source animation proof, but no additional isolated browser animation suite. Those are not counted among the seven fresh browser animation cases.
- No Gallery component-playback UI was added.
- Metadata remains draft. No engineering, medical, traffic or safety certification is claimed.
- No production deployment or remote publication was performed by this integration worker.
- The library report retains an inaccurate inherited macOS label. Actual integration ran on Ubuntu Chromium with SwiftShader.

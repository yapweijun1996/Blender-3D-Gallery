# Five-Foot-Way Floor Tile verification

Backlog 398. **Local artifact audit: PASS. Overall: NEEDS REVIEW.**

## Current recovery audit, 2026-11-13 UTC

- Independent source, GLB, generator, three-angle PNG/WebP previews, metadata, and source-edit evidence are present.
- Current source and export SHA-256 values match the producer's source report and metadata:
  - Source: `51add5b7f4331722c91fca9b1c0eeec3b940c8dab48f52c7f468fceef178772b`
  - GLB: `a761e7461fbd92ba7ced406261514af31c93818d0efba0894457bbc277e7c54e`
- Current GLB: 29,324 bytes, 276 triangles, 23 mesh primitives, 4 materials. Recorded Khronos validation: zero errors and zero warnings.
- Units: metres; Blender +Z / glTF +Y up; Blender -Y / glTF +Z front; ground-plane origin.
- Actual shipped hero, front and rear WebP pixels were independently inspected. The simple form is recognizable, grounded and unclipped; no obvious floating parts or blocking visual defect was seen. Visible studio grain is not represented as photorealistic quality.
- The recovered assembly's source/export hashes were checked again before this document was written. This audit did not regenerate the asset or rerun the browser suite.

## Preserved producer evidence

- [Structure and budgets](reports/assets.json), [source inspection](reports/source.json), [source-edit proof](reports/source-edit-proof.json).
- The source inspector opens the delivered source, checks metric units, independent mesh data and finite coordinates, saves an edited copy, and exports that copy. The source-edit validator checks the changed GLB and its expected geometric change.
- [Historical browser log](reports/browser.log): 3/3 viewport cases passed at 1440, 768 and 390 px. Detailed results and screenshots remain in reports/browser.
- Producer-wide unit/build evidence is retained under ../zebra-crossing-beacon/reports/unit-final.log and build-final.log: 235 tests passed and the build completed. These are historical producer results, not current combined-assembly results.

## Pending combined gate and limits

The new combined assembly based on main `85ceaa9` is awaiting its fresh test/build/browser/lifecycle/library gate. Its eventual combined report supersedes this pending-at-authoring statement without erasing historical evidence.

Physical Android/iOS devices, native mobile browsers/GPUs, touch behavior and Safari/WebKit are NOT TESTED. Desktop Chromium viewport tests are not real-device acceptance. This is a static visual prop with independently editable source components, not a runtime control, animation, certified installation or official regulatory design. Public redistribution terms are unspecified; existing owner-project reuse rights and disabled downloads remain unchanged. No release or deployment is claimed.

# Street Utility Pole verification

Backlog 399. **Local artifact audit: PASS. Overall: NEEDS REVIEW.**

## Current recovery audit, 2026-11-13 UTC

- Independent source, GLB, generator, three-angle PNG/WebP previews, metadata, and source-edit evidence are present.
- Current source and export SHA-256 values match the producer's source report and metadata:
  - Source: `b5a67b962f41f171ebcaa070bc95234ed816f4768d86df4f72039fa283cf443c`
  - GLB: `76903b7a053c4e448acf17945b0b76b1120b3422ab4958b3b765a51c1f1052f9`
- Current GLB: 76,904 bytes, 1,496 triangles, 22 mesh primitives, 4 materials. Recorded Khronos validation: zero errors and zero warnings.
- Units: metres; Blender +Z / glTF +Y up; Blender -Y / glTF +Z front; ground-plane origin.
- Actual shipped hero, front and rear WebP pixels were independently inspected. The simple form is recognizable, grounded and unclipped; no obvious floating parts or blocking visual defect was seen. Visible studio grain is not represented as photorealistic quality.
- The recovered assembly's source/export hashes were checked again before this document was written. This audit did not regenerate the asset or rerun the browser suite.

## Preserved producer evidence

- [Structure and budgets](reports/assets.json), [source inspection](reports/source.json), [source-edit proof](reports/source-edit-proof.json).
- The source inspector opens the delivered source, checks metric units, independent mesh data and finite coordinates, saves an edited copy, and exports that copy. The source-edit validator checks the changed GLB and its expected geometric change.
- [Historical browser log](reports/browser.log): 3/3 viewport cases passed at 1440, 768 and 390 px. Detailed results and screenshots remain in reports/browser.
- Producer-wide unit/build evidence is retained under ../zebra-crossing-beacon/reports/unit-final.log and build-final.log: 235 tests passed and the build completed. These are historical producer results, not current combined-assembly results.
The initial pole extended into the central insulator. The corrected pole ends at 6.5 m, below the insulators; explicit clearance assertions are in validate.mjs. Initial source, GLB and evidence are retained in reports/initial-source. Initial low-contrast studio renders are retained in reports/initial-studio. Use validation-final.log for the current GLB, not the historic validation.log.

## Pending combined gate and limits

The new combined assembly based on main `85ceaa9` is awaiting its fresh test/build/browser/lifecycle/library gate. Its eventual combined report supersedes this pending-at-authoring statement without erasing historical evidence.

Physical Android/iOS devices, native mobile browsers/GPUs, touch behavior and Safari/WebKit are NOT TESTED. Desktop Chromium viewport tests are not real-device acceptance. This is a static visual prop with independently editable source components, not a runtime control, animation, certified installation or official regulatory design. Public redistribution terms are unspecified; existing owner-project reuse rights and disabled downloads remain unchanged. No release or deployment is claimed.

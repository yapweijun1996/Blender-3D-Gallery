# F06 acceptance evidence

Candidate exported with Blender 5.1.2 and Khronos glTF Blender I/O 5.1.20 on 2026-11-23.

| Input | SHA-256 |
| --- | --- |
| Festival concept board | `c375207b8e3ed268e762eb60d19612144d0a0f2a4e0eacca3b927a709ce318c9` |
| Blender source | `a2a308f59ba3fb0b2b3799b6171628ab2cb799bc55e62a5bff449f84a4d546d9` |
| GLB | `e7edb8beb6fb60347d448cb52501ef757f39ebff9bba62a27af2fad452c5ae5b` |
| Hero thumbnail | `f2184f236be405690c6ade22896ffd1192b71565fdaf4165c132b5a20c713516` |

## Independent visual review

A separate reviewer compared the standalone rabbit in the concept board's
lower-left panel with four 640 × 640 Cycles renders reimported from the exact
GLB and the actual thumbnail at 160 px. The back and opposite side interpret
surfaces the concept does not show.

| Required feature | Result | Capture |
| --- | --- | --- |
| Recognizable seated rabbit, tilted ears and rounded head and body | PASS | [Hero](previews/hero.webp), [front](previews/front.webp) |
| Rose ear panels, small dark eyes and coral nose | PASS | [Hero](previews/hero.webp), [front](previews/front.webp) |
| Warm paper, fine honey bamboo ribs and a coral branch motif | PASS | [Hero](previews/hero.webp), [opposite side](previews/other-side.webp) |
| Paws, tail and ears appear connected through rotation | PASS | [Front](previews/front.webp), [rear](previews/rear.webp) |
| Readable rabbit and ornament at thumbnail scale | PASS | [Hero](previews/hero.webp) |

The paper has a softer glow than the concept. The rose is strongest in the
hero view and reads edge-on from the front. The scope is an original stylized
model.

## Technical and local runtime checks

- Khronos glTF Validator passed with zero errors and warnings. Three.js parsed
  the expected root and measured a 0.631 × 0.744 × 0.316 m bounding box.
  The 1,215,752-byte GLB has 55,712 triangles, 31,164 vertices, 8 materials,
  8 draw calls and no clips or external resources.
- Blender reopened the file with embedded script execution disabled and
  confirmed 141 independently editable meshes. A clean rebuild from the
  generator alone preserved the glTF JSON, vertex positions, triangle sets
  and bounds. Some export index ordering and small normal values varied,
  so the rebuilt GLB was not byte-identical to the reviewed export.
- Node 24 full build and asset validation passed, as did all 813 default tests.
- Local Chromium at 1440 × 900 and emulated 390 × 844 verified search, no GLB
  fetch before opening, exact response bytes, WebGL drawing, rotation, reset,
  download control absence and viewer close, with no console errors or
  horizontal overflow. An injected HTTP 503 preserved the descriptive poster
  and the retry recovered the exact GLB.
- Physical devices and screen-reader hardware were not tested.

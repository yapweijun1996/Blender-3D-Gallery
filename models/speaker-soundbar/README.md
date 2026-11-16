# Speaker and Soundbar

Original brand-neutral audio display for GJH Virtual Mall stores S13/S14, priority P2. Existing category: **Equipment**. Status: draft / **NEEDS REVIEW** for manager art review. Original procedural geometry, materials and woven-cloth colour/normal tiles only; no external assets, text, logos or product packaging.

Two independent named nodes retain floor-level placement pivots: `SOUNDBAR` and `FLOOR_SPEAKER`. The graphite soundbar has a woven centre grille, two visible cones, three blank tactile buttons, floor pads and rear connector forms. The speaker has two larger cones, a tweeter, woven side grilles, reflex-port form, a plinth, floor pads and rear binding posts. These are static visual props with no sound or electrical behavior.

Measured GLB dimensions, in width × height × depth: soundbar 0.89999998 × 0.09730000 × 0.15994000 m; speaker 0.28000000 × 0.89999998 × 0.31999999 m. Combined display: 1.33999996 × 0.89999998 × 0.31999999 m. Export: 13,632 triangles, 872,436 bytes, two stored meshes, six primitives, three shared opaque materials and two embedded 128 × 128 original PNG tiles. The native source preserves 44 editable solid mesh parts. Studio floor, lights and camera are excluded from GLB.

Metres; combined origin at the floor centre of the display footprint. Blender +Z up / -Y front exports to glTF +Y up / +Z front. The two product nodes can be moved independently; their saved local X offsets form only the display arrangement.

From the repository root:

```sh
/opt/homebrew/bin/blender --background --python models/speaker-soundbar/generate.py
node models/speaker-soundbar/validate.mjs
/opt/homebrew/bin/blender --background --python models/speaker-soundbar/inspect_sources.py
node models/speaker-soundbar/verify_source_edit.mjs
npm run validate:assets
npm test
npm run build
node models/speaker-soundbar/verify_page.mjs
```

Generator options after `--`: `--skip-render`, `--views=hero,front,side,3q,rear`, or `--export-source` to export the saved source without rebuilding. Export batches evaluated copies, preserves saved edits and leaves the native source unchanged. Inspection uses disposable copies under the system temporary directory. Rebuilding replaces this asset's source/export/previews.

Evidence: [duplicate search](reports/duplicate-search.json), [measured GLB](reports/assets.json), [Khronos](reports/khronos.json), [source editing](reports/sources.json), [rebuild](reports/reproducibility.json), [browser](reports/browser.json) and [acceptance](reports/acceptance.json). Node texture loading checks structural dimensions; the real texture pixels are rendered in Blender and Chromium.

No close audio-model match was found before production. Physical Android/iOS, WebKit, full 17-shop assembly, the combined mall's 200 draw-call budget, acoustic/electrical operation and deployment remain unverified. Local per-model checks do not establish those outcomes. No push or publication is included.

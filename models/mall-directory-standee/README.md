# Mall Directory Standee

Original P3 atrium fixture in the existing **Mall Fixtures** category. Two blank warm ivory backlit panels, unlabelled locator dots, deep jade housing, champagne trim, a slim weighted foot and a small top light bar. No text, map artwork, logos, fonts, downloaded assets or textures. Static geometry; the emissive material does not create runtime scene lights or navigation.

The exported GLB measures **0.900 m wide × 0.350 m deep × 1.900 m high** (rounded from measured bounds). It contains **3,316 triangles, 4,959 vertices, 5 mesh primitives, 3 shared materials, zero animations**, and is **142,988 bytes**. Origin is the floor centre; Blender +Z up / -Y front exports to glTF +Y up / +Z front. Each panel measures 0.752 × 1.408 m, with a 0.038 m diameter plain locator dot. Source retains 19 separate editable mesh parts and bevel modifiers; delivery batches those parts by material and logical role.

From this directory:

```sh
/opt/homebrew/bin/blender --background --python-exit-code 1 --python generate.py
/opt/homebrew/bin/blender --background sources/mall-directory-standee.blend --python-exit-code 1 --python inspect_source.py
/opt/homebrew/bin/blender --background --python-exit-code 1 --python generate.py -- --export-source --skip-render --export-path /tmp/mall-directory-standee-source.glb
node validate.mjs
```

Use `--export-source` to export saved edits; the default command rebuilds the original design. `--skip-render` omits previews. `--export-path` allows comparison without overwriting the delivery GLB. The isolated generator-only rebuild and saved-source re-export produced the same GLB SHA-256: `639fd4bb992d9453326c04dc936f727d870368fcee8a0cacc651d9a8cf59b4e6`.

From the repository root:

```sh
npm run validate:assets
npm test
npm run build
node models/mall-directory-standee/check_page.mjs
```

`reports/acceptance.json` records final command results; `reports/assets.json`, `khronos.json`, `source.json`, `reproducibility.json` and `browser.json` retain measured evidence. Previews are hero, front, side, 3q and rear PNGs, all visually inspected. The browser check consumes the tested GLB by SHA-256 at 1440 × 900 and saves the requested screenshot under `~/Documents/MallQueue/reports/`.

Duplicate search: 619 catalog assets and 662 metadata files searched before building. **Exact match NOT FOUND.** `mall-directory-kiosk` is single-sided with labels, a map and a rear service cover. `mall-advertising-lightbox` is single-sided with campaign artwork. Floor and ceiling wayfinding signs have directional labels and different mounting. They lack this requested blank double-sided directory configuration; all existing models remain intact. See `reports/duplicate-search.json`.

Status remains **draft / NEEDS REVIEW** for owner review. Physical phones, WebKit, full-mall performance, electrical lighting, installation stability, physical safety and live publication have not been verified. Five GLB primitives describe this asset's base drawing cost, not a measured 200-call whole-mall result. No UI, workflows, deployment or existing models were intentionally changed.

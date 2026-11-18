# GJH v11 interior fixture build

This delivery contains eight original entrance fixtures and nine owner-project library derivatives. Each catalog entry opens the highest delivered tier. GJH selects one standalone GLB per anchor. The staging manifest binds each runtime filename to its measured geometry, byte size, SHA-256, material, source, author and licence. [Staging manifest](../exports/gjh-v11-interiors/manifest.json) · [Exact placement transforms](../exports/gjh-v11-interiors/README.md)

## Rebuild

Start at the gallery repository root. Use Blender 5.1.2, its bundled NumPy and glTF exporter, Python 3, Node/npm from the repository toolchain and `cwebp`. Install the locked npm dependencies with `npm ci` in a fresh checkout. The self-contained [programme extract](../scripts/gjh_interiors/program.json) records the authoritative Phase 1 JSON digest, the ordered new-model briefs, each anchor, its palette, placement and per-tier cap. The nine derivatives read the original repository GLB and blend fingerprints before reading native mesh data with script execution disabled.

```sh
/Applications/Blender.app/Contents/MacOS/Blender -b -noaudio --factory-startup --disable-autoexec \
  --python-exit-code 1 --python scripts/gjh_interiors/build.py
node scripts/gjh_interiors/validate.mjs --write
python3 scripts/gjh_interiors/package.py
node scripts/gjh_interiors/validate.mjs
python3 scripts/gjh_interiors/package.py --check
npm run validate:assets
npm test
npm run build
```

The default Blender command builds in programme order, then derives the nine library anchors. Append `-- --model collector-triptych` to build a single entry. Use `--geometry-only` or `--previews-only` after the argument separator to run that part of the build. Each model also has a direct `models/<slug>/generate.py` entry point. Run the validator and packager after changes.

### macOS headless invocation

The build used the signage kit's process-local Metal startup workaround with the installed Blender binary. The application copy and user resources are temporary. Cycles renders on the CPU.

```sh
signage_work=$(mktemp -d)
cat > "$signage_work/metal-null-guard.c" <<'C'
#include <string.h>
static char *guarded_strstr(const char *haystack, const char *needle)
{
    return haystack == NULL ? NULL : strstr(haystack, needle);
}
__attribute__((used, section("__DATA,__interpose")))
static const struct { const void *replacement; const void *original; }
guard = { (const void *)guarded_strstr, (const void *)strstr };
C
clang -dynamiclib "$signage_work/metal-null-guard.c" -o "$signage_work/metal-null-guard.dylib"
mkdir -p "$signage_work/Blender.app/Contents/MacOS"
cp /Applications/Blender.app/Contents/MacOS/Blender "$signage_work/Blender.app/Contents/MacOS/"
ln -s /Applications/Blender.app/Contents/Resources "$signage_work/Blender.app/Contents/Resources"
signage_blender="$signage_work/Blender.app/Contents/MacOS/Blender"
codesign --force --sign - "$signage_blender"
BLENDER_USER_RESOURCES="$signage_work/user" DYLD_INSERT_LIBRARIES="$signage_work/metal-null-guard.dylib" \
  "$signage_blender" -b -noaudio --factory-startup --disable-autoexec \
  --python-exit-code 1 --python scripts/gjh_interiors/build.py
```

## Authoring and placement

The eight masters have individual generators. Each highest-tier blend has one bottom-centred root, named removable mesh parts and packed images. All LODs use metres, Blender +Z up / −Y front and glTF +Y up / +Z front. The collector, suspended hood and screen use the bottom of their mounting envelope as the local datum. For an anchor on a separate stand, its installation height already includes the planned support. The runtime parent supplies the slot transform. Do not apply the envelope as a second scale.

Each store uses a shared opaque PBR material. Four columns of a 256 × 256 embedded colour atlas correspond to the four exact programme swatches. Its rows contain neutral swatches, grain, fixture-specific baked detail and an inset border. A packed map stores roughness in green and metallic in blue. The opal index adds an opaque emissive edge, and the eyelet rail colours its lanyard with a vertex attribute. Finishes, blank display faces and architectural profiles are original. Official art is applied in GJH.

Primary previews are 512 px Cycles renders from reimported catalog GLBs. Each model also includes a 393 px Low render in `reports/low-393.png`. The render receipts identify the exact input and image files. One camera angle looks under the hood to expose its filter banks.

## Measured delivery

Triangle counts include every visible mesh instance in the default scene. File sizes are exact bytes for one complete GLB. The staging copy must match the corresponding gallery export byte for byte.

<!-- metrics:start -->

| Store | Model | Low tris / bytes | Balanced tris / bytes | Detailed tris / bytes |
|---|---|---:|---:|---:|
| S01 | [collector-triptych](../models/collector-triptych/README.md) | 412 / 41,552 | 1,236 / 97,576 | 2,044 / 133,608 |
| S02 | [hawker-stall-exhaust-hood](../models/gjh-hawker-stall-exhaust-hood/README.md) | 468 / 38,936 | 692 / 56,428 | — |
| S03 | [ice-cream-cart-potong](../models/gjh-ice-cream-cart-potong/README.md) | 748 / 57,460 | 2,326 / 150,476 | — |
| S04 | [patch-folio](../models/patch-folio/README.md) | 204 / 26,892 | 844 / 75,300 | 1,524 / 103,268 |
| S05 | [specimen-drawers](../models/specimen-drawers/README.md) | 500 / 45,516 | 1,764 / 133,736 | 2,228 / 145,484 |
| S06 | [noodle-loom](../models/noodle-loom/README.md) | 540 / 52,960 | 1,376 / 111,984 | 2,580 / 182,128 |
| S07 | [stacked-can-pyramid](../models/gjh-stacked-can-pyramid/README.md) | 708 / 42,456 | 2,426 / 162,152 | — |
| S08 | [peanut-butter-jar-stand](../models/gjh-peanut-butter-jar-stand/README.md) | 768 / 60,780 | 2,388 / 111,012 | — |
| S09 | [conveyor-belt](../models/gjh-conveyor-belt/README.md) | 176 / 22,728 | 560 / 50,592 | — |
| S10 | [nacre-cradle](../models/nacre-cradle/README.md) | 696 / 49,888 | 2,216 / 91,528 | 5,104 / 160,204 |
| S11 | [packing-station](../models/gjh-packing-station/README.md) | 276 / 29,088 | 748 / 63,544 | — |
| S12 | [opal-index](../models/opal-index/README.md) | 232 / 30,636 | 824 / 75,168 | 1,240 / 91,240 |
| S13 | [headphone-display-stand](../models/gjh-headphone-display-stand/README.md) | 780 / 55,696 | 2,508 / 163,820 | — |
| S14 | [tv-wall-mounted](../models/gjh-tv-wall-mounted/README.md) | 108 / 34,300 | 360 / 53,492 | — |
| S15 | [grand-piano](../models/gjh-grand-piano/README.md) | 912 / 68,504 | 2,704 / 186,224 | — |
| S16 | [eyelet-rail](../models/eyelet-rail/README.md) | 544 / 59,820 | 1,152 / 107,836 | 1,600 / 123,736 |
| S17 | [telephone-alcove](../models/telephone-alcove/README.md) | 200 / 28,284 | 692 / 66,384 | 1,100 / 80,676 |

Measured Low anchors total **8,272 triangles**. Substituting them into the 17 complete Phase 1 allocations projects **30,518 triangles** across all shops and **2,480** for the largest shop. The remaining room geometry is budgeted.

<!-- metrics:end -->

## Rights and provenance

The new masters copy the existing packing-station model licence verbatim. The nine derivatives retain their respective source licence files verbatim and quote the source metadata's author, rights and credits. Authorised scope is reuse in the owner's projects. General public redistribution terms are unspecified. Each derivative records both source paths and hashes, its reconstruction method and the store palette in its metadata. The manifest carries the rights with the runtime files. All nine selected source records include the owner-project grant. Rejected sources among these nine: zero. [Existing model licence](../models/packing-station/LICENSE.md)

## Verification and limits

The per-model `reports/khronos.json` files contain the Khronos glTF Validator version, input hashes and every issue for every tier. The independent Python check reads the final GLB positions and indices, walks the active scene, checks opposing triangle edges and positive signed shell volumes after positional seam welding, rejects zero-area faces, and verifies the static PBR profile, named groups, bounds, installation datum, tier caps and staged bytes. It also reads the exact RGB values of the four embedded swatches. The packager checks source rights, preview hashes and both Low budgets.

- All 42 GLBs passed Khronos glTF Validator 2.0.0-dev.3.10 with zero errors and zero warnings. A second geometry build reproduced every GLB byte for byte. All 17 saved blends reopened with packed images and metric scene units.
- All 17 slot transforms, 42 tier assignments, source credits and staged hashes were separately compared with the read-only Phase 1 JSON. Each fixture was visually inspected from reimported GLBs, including its 393 px Low view. The final Low headphone bands reach the ear cups.
- The repository production build passed, including its full asset validator (679 catalog GLBs plus the chibi and pomelo checks). All 744 Node tests passed, along with the i18n, colour-token and contrast checks. The repository's Blender/Python shopping-mall calibration passed with the locally installed texel-density and 3D-print extensions.
- Vite reported its bundle-size advisory for JavaScript chunks over 500 kB. Blender emitted a sampler advisory when combining metallic/roughness channels from one packed image and could not cache some system thumbnails in the sandbox. The saved sources, embedded maps and rendered previews were verified separately.
- The gallery browser suite stopped at local server startup because this sandbox denied a loopback listen with `EPERM`. Standalone Chromium headless launch also failed before page creation. The 393 px evidence is a CPU render. Browser, WebGL and physical-phone interaction remain **UNVERIFIED**.

**UNVERIFIED** — Final GJH scene placement, visibility switching, stock and support assemblies, collisions and picking, real-device frame time and renderer draw calls. The full-room figure substitutes measured focal anchors into the Phase 1 allocation. It includes allowances for other geometry, including the secondary window displays. The 17 measured assets cover the entrance anchors. Review, runtime integration and publication belong to the manager.

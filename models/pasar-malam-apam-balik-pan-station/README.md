# Pasar Malam Apam Balik Pan Station

An original unbranded tabletop market exhibit: two differently patinated circular pans with real bowls and rolled lips, a detached domed lid parked on a separate support, and one original folded sample resting on a visibly open wire rack. Nothing operates. This is not a site reconstruction, model of a named merchant's equipment, cooking recipe, stove instructions or a claim that all apam balik stalls use the same pan/lid.

- The [Malaysian Department of National Heritage list](https://www.heritage.gov.my/en/2009.html) includes apam balik. [Bintulu Development Authority](https://www.bda.gov.my/web/subpage/webpage_view/49) documents it as a night-market food.
- [Field documentation from UNINESS](https://uniness.gallery/apam-balik-in-petaling-street/) describes a round pan with removable lid in one actual Malaysian street-commerce setting; [a Malaysian cookware maker](https://www.metallogy96.com/collection/apam-balik) lists apam balik mould and wire rack types. Only these general types inspired the exhibit. No vendor identity, artwork, logo or prefabricated shape was copied.
- All geometry, lettering, baked vertex colours and pore-shaped crust marks are original. No external model or texture.
- Blender 4.3.2, floor origin, +Z up/−Y front; glTF +Y up/+Z front, scene units in metres. Reference probes measure only the fictional model.
- Reproduce: `blender -b --python-exit-code 9 --python generate.py -- --output /tmp/new-apam-pan-station`. `--skip-render` exports only Blender/GLB; `--review /tmp/apam-angle-checks` creates separate inspection images.
- Verify GLB/Khronos and Three.js with `node verify.mjs`; inspect edited native and exact re-imported geometry: `blender -b --python-exit-code 9 --python verify_blender.py`.

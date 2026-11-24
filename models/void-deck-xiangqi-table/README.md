# Void Deck Xiangqi Table

An original Singapore void-deck setting: a heavy cast terrazzo table, four cast stools and a built-in Chinese chess board. The grid is modeled as inlays and has nine files, ten ranks, an open river between the centre ranks and two crossed palaces. Ten individually modeled and labeled pieces make up an illustrative partial position. The generals sit in opposite palaces with a piece between them. This is a static display, not a playable board or a reconstruction of a historical game, flat or public housing site.

Singapore's [National Heritage Board, *Void Decks*](https://www.nhb.gov.sg/~/media/nhb/files/resources/publications/ebooks/nhb_ebook_void_decks.pdf) documents chess in the shared setting; the [World Xiangqi Rules, §1](https://www.wxf-xiangqi.org/images/wxf-rules/2018_World_XiangQi_Rules_English2018.pdf) informed the grid. No reference photograph, table design, logo or typeface outlines are reused. The restrained aggregate chips and small monoline markings are original meshes.

## Reproduce and validate

- Blender 5.3.0: `blender -b --factory-startup --threads 5 --python-exit-code 31 --python generate.py -- --output .`. Add `--review <dir>` for the native top and pedestal views, or `--skip-render` for the source and GLB only. Independent same-version regeneration produced the identical GLB bytes.
- For native and re-imported inlay rays, cast forms and exact piece locations: `blender -b --factory-startup void-deck-xiangqi-table.blend --python-exit-code 31 --python verify_blender.py -- exports/void-deck-xiangqi-table.glb`.
- From the repository root, `node models/void-deck-xiangqi-table/verify.mjs` checks Khronos conformance, GLB mesh names, slots and SHA-256 digests.

Illustrative metres; Blender +Z up and −Y outward, glTF +Y up and +Z outward. The scene is not a construction standard or public-site identification. Camera and lighting are not exported. Original project asset; public download redistribution terms are unspecified.

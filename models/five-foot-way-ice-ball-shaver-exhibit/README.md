# Five-Foot Way Ice-Ball Shaver Exhibit

Original static exhibit inspired by the hand-sliding ice shavers associated with historical Singapore itinerant ice-ball vendors. It shows a wooden deck with a real open slot, rounded neutral trim, a staged opaque ice prop and an empty enamel bowl. The dark display plinth is fictional. This does not reproduce a particular vendor's tool, portray operation or contain an operative blade, a recipe, or a food-handling or certification claim.

[National Heritage Board, Heritage Along Footpaths](https://www.nhb.gov.sg/~/media/nhb/files/resources/publications/ebooks/nhb_ebook_heritage_along_footpaths.pdf), printed page 13, is the first-party historical context for the vendors and shaver fixture. All forms, presentation and color are original.

Blender 4.3.2, sources +Z up/-Y front and GLB +Y up/+Z front. Use `--skip-render` for editable source and GLB only.

```sh
blender -b --python-exit-code 4 --python generate.py -- --output ./generated
blender -b --python-exit-code 5 --python verify_blender.py -- ./generated
node verify.mjs ./generated/exports/five-foot-way-ice-ball-shaver-exhibit.glb
```

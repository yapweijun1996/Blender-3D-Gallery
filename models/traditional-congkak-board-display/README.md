# Traditional Congkak Board Display

Original static display inspired by Malaysian congkak. A single rounded timber shape has two parallel rows of seven individually recessed wells and one larger end well at either end. The wells are physically carved into the editable mesh; nine plain seed-like display markers are staged without representing a starting position, playable simulation or rules. The low blue exhibit support is separate from the board. The shape, muted finish and seed geometry are original, not copies of a collection item or of a ceremonial motif.

- [Malaysia JKKN arts and culture register, Congkak](https://pemetaanbudaya.jkkn.gov.my/en/senibudaya/detail/1344) documents the common seven-per-side variation and two larger end wells, alongside other forms.
- [Department of Museums Malaysia, Perak Museum](https://www.jmm.gov.my/ms/content/muzium-perak-0) provides context for the game's inclusion in traditional-games exhibitions, not for this model's dimensions, finish or display stand.

## Reproduce and verify

Run locally with Blender 4.3.2 and the Gallery's standard Node development dependencies. Blender is +Z up/-Y front; GLB is +Y up/+Z front. The model has no animations or external textures.

```sh
blender -b --python-exit-code 4 --python generate.py -- --output ./generated
blender -b --python-exit-code 5 --python verify_blender.py -- ./generated
node verify.mjs ./generated/exports/traditional-congkak-board-display.glb
```

Add `--skip-render` if only the editable source and GLB are needed.

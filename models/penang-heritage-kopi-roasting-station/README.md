# Penang Heritage Kopi Roasting Station

An original static display inspired by documented coffee-roasting workshops in George Town, Penang. It combines a physically recessed cast pot and open masonry exhibit with a small fixed coffee-bean sample, two independently parked hardwood paddles, and a separate pulley-and-cord display. The pulley does not connect to or drive the pot. No real heat, roasting motion, recipe, make, surveyed location or particular workshop's design is reproduced.

The brick pieces, threaded rope path, pot saddle, and tooling are editable. Blender uses +Z up; the Gallery GLB uses +Y up and +Z front. The individual meshes and colors are original. The asset has no external image, video, sound or mechanism simulation.

## Context

- [George Town World Heritage Site Visual Guide](https://www.mypenang.gov.my/uploads/downloads/0_170714_1650275027_gtwhi_map_web_pdf.pdf), for the documented presence of traditional coffee roasters.
- [Kopi Museum at Coffee Atelier](https://coffeeatelier.com/kopi/), first-party documentation of the separate types of historic pot stoves, equipment pulleys, and wooden paddles in a Penang workshop. The arrangement and visual design here are original and not a replica of that site.

## Reproduce and verify

Run with Blender 4.3.2 from this directory:

```sh
blender -b --python-exit-code 4 --python generate.py -- --output ./generated
blender -b --python-exit-code 5 --python verify_blender.py -- ./generated
node verify.mjs ./generated/exports/penang-heritage-kopi-roasting-station.glb
```

Use `--skip-render` for the editable native file and GLB only.

# Proton Saga (1985) — silver heritage study

Original Blender interpretation of the first Saga four-door sedan, refined using the owner's two heritage showcase reference images. The silver body has a profiled bonnet and boot, open wheel arches, steel wheels with hubcaps and subtle tread, rectangular fluted lamps, segmented rear lamps, a horizontal grille, black bumpers and red coachlines. Window frames, door outlines, handles, mirrors, fuel flap, exhaust, wipers, antenna and display plates are modeled geometry. Smoky glazing reveals a basic right-hand-drive cabin with seats, dashboard and steering wheel.

The model remains an approximate artistic reconstruction: proportions, panel curves, trim, lighting, interior and mechanical details are simplified. It does not establish an exact factory specification, original paint code or road registration. No engine or opening panels are modeled. The simple shield badge is original geometry rather than a reproduction of official emblem artwork.

## Reproduce

Requires Blender 5.1.2 and `cwebp`. From the repository root:

```sh
/Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup --python models/proton-saga-1985/generate.py
```

The deterministic generator replaces the GLB, editable `scene.blend`, `preview.webp`, and the four studio renders `view-front.webp`, `view-rear.webp`, `view-left.webp`, `view-right.webp`. Intermediate PNGs are converted and removed automatically. Metadata and this document are maintained separately and preserved. The GLB contains only `ASSET_Proton_Saga_1985` and its descendants; studio floor, camera and lights remain in the Blender source. No random seed, external images, downloaded scripts or third-party meshes are required.

Blender front is −X, physical left is −Y and up is +Z. The four views use the same charcoal studio, lighting, framing and silver/black/red materials. They are genuine renders of the exported geometry, not reference photographs.

## Provenance and rights

Historical sources: [PROTON milestones](https://www.proton.com/corporate/milestones) and [PROTON heritage gallery](https://www.proton.com/happenings/2021/november/proton-unveils-new-brand-gallery). Owner-supplied reference images guided the silver vehicle's appearance. All references were viewed only and are not bundled or embedded. Artwork redistribution terms remain pending owner decision; vehicle names identify the subject and imply no endorsement. See `metadata.json` for measured export metrics and accuracy limits.

Run `npm run validate:assets` for glTF structural validation and `node scripts/test-saga-browser.mjs` for the actual viewer. Desktop/mobile Chromium evidence does not establish compatibility with every physical device or rendering engine.

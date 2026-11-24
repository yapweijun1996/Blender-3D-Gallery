# Woven Bubu Fish-Trap Display

An original static museum-style interpretation of a Malaysian woven bubu form. A curved bamboo-colored lattice tapers to a wrapped end. The broad rim carries a separately woven inward funnel with a genuine open throat into the hollow body. Two independent blue-green display saddles support it without concealing the lattice. The display is empty, with no fishing process, live animals, instructions, replica, or claim that every regional bubu takes this form.

The visible longitudinal strips, cross bands, entrance and throat rings, and independent supports are editable meshes. The colors and the models are original. Blender +Z is up; GLB +Y is up and +Z front. There are no external media, shaders simulating solid weave, or animation clips.

## Context

- [Perlis State Public Library, Alat-alat Menangkap Ikan Air Tawar](https://www.perlislib.gov.my/web/ejurnal-perlis/382-alat-alat-menangkap-ikan-air-tawar-2), for the documented separately inward-narrowing insert on one Malaysian form; no proportions, patterns, or procedure copied.
- [Museum Volunteers, Department of Museums Malaysia, September 2024](https://museumvolunteersjmm.com/2024/09/), firsthand description of displayed fiber craft, including a tapered barrel and separate funnel.
- [Dewan Bahasa dan Pustaka, bubu](https://prpm.dbp.gov.my/Cari1?d=72508&keyword=bubu), for the general name and its application to multiple forms.

## Reproduce and check

Run with Blender 4.3.2 from this directory:

```sh
blender -b --python-exit-code 4 --python generate.py -- --output ./generated
blender -b --python-exit-code 5 --python verify_blender.py -- ./generated
node verify.mjs ./generated/exports/woven-bubu-fish-trap-display.glb
```

Use `--skip-render` for the editable Blender file and static GLB only.

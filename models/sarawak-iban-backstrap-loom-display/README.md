# Sarawak Iban Backstrap Loom Display

This original, static exhibit is inspired by Iban backstrap weaving in Sarawak, including the documented loom type used for pua kumbu. The sample is an original plain-weave study with simple colour bands, not a reproduction of pua kumbu, ceremonial textile, or named artifact. There is no model of a weaving workflow. The dark-blue exhibition supports and padded strap rest are modern supports added for display, not part of a traditional rigid loom frame.

The wood beams, 36 individually modeled continuous warp strands, 21 solid weft courses, 18 encircling heddle cords and two breast-beam strap ties are separately editable. The isolated wordmark is a generic exhibit caption. Blender uses +Z up; the GLB uses +Y up and +Z front.

## Context references

- [Sarawak Museum Department, Textile](https://museum.sarawak.gov.my/web/subpage/webpage_view/109), for local warp-ikat textile context and its significance to the Iban.
- [Universiti Malaysia Sarawak repository, Alat Ritual dalam Budaya Masyarakat Iban Sarawak](https://ir.unimas.my/id/eprint/30489/5/Alat%20Ritual%20Dalam%20Budaya%20Masyarakat%20Iban%20Sarawak.pdf), for identifying the backstrap loom type in the documented textile context.
- [National Museums Scotland, West, South and Southeast Asia collection](https://www.nms.ac.uk/collections/departments/global-arts-cultures-design/asia/west-south-and-southeast-asia), for collection documentation of an in-progress Sarawak textile with loom and tools; no named person's craft or design is copied.
- [Ikat Textiles from Sarawak in National Museums Scotland's Collection](https://www.orientalrugandtextilesociety.org.uk/_files/ugd/a762d0_de72114efe7e4016b0563f44e30e4f19.pdf), museum collection account for discrete wood bars, breast and warp beams, and connecting strap. Not a dimension or assembly reference.

## Reproduce and check

Run from this directory with Blender 4.3.2:

```sh
blender -b --python-exit-code 4 --python generate.py -- --output ./generated
blender -b --python-exit-code 5 --python verify_blender.py -- ./generated
node verify.mjs ./generated/exports/sarawak-iban-backstrap-loom-display.glb
```

Use `--skip-render` if only the editable Blender file and static GLB are needed. The asset contains no external imagery, cloth textures, animation, or audio.

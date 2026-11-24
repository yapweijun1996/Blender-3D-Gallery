# Mall Entrance Air-Curtain Cutaway

An original, static section through a fictional mall doorway header. Eleven independent grille slats remain on the left; an exposed section shows two hollow transverse blade cages, fixed shafts, and recessed metal walls around one continuous open lower discharge slot. The assembly is a dry gallery exhibit, not an airflow simulation, construction or installation drawing, or a claimed air-curtain performance measure.

Context only: the [Singapore Building and Construction Authority environmental sustainability FAQ](https://www1.bca.gov.sg/docs/default-source/docs-corp-buildsg/sustainability/faq-on-environmental-sustainability-requirements.pdf?sfvrsn=d085b179_31) describes air curtains in Singapore building-door scenarios. [ASSA ABLOY Singapore](https://www.assaabloy.com/sg/en/solutions/industries/retail/shopping-malls) also describes air curtains at shopping-mall doors. Separate first-party component context comes from [Berner's recessed front entrance range](https://berner.com/application/main-entrance/) and [Acme's cross-flow overview](https://www.acmeaircurtain.com/why-choose-cross-flow-suction-air-curtains-over-centrifugal-suction-air-curtains/). No commercial design, lettering, dimensions, photos, installation or other engineering specifications were copied.

## Editable geometry

Blender 5.3.0, built-in mesh and typeface tools, no downloaded dependencies. Blender +Z is up, -Y forward; glTF +Y is up, +Z forward. Both export and gallery preview contain no animation or external textures. Studio equipment is excluded from GLB.

```sh
blender -b --factory-startup -P generate.py -- --output /tmp/air-curtain --review /tmp/air-curtain-reviews
blender -b --factory-startup --python-exit-code 9 -P verify_blender.py -- \
  mall-entrance-air-curtain-cutaway.blend exports/mall-entrance-air-curtain-cutaway.glb
node verify.mjs
```

Blender and an independent GLB import check open grille and outlet surfaces, spokes and shaft joints, and the actual gaps between discrete modeled blade surfaces. Three GLTFLoader repeats through-ray measurements on the shipped geometry. All tests describe this illustrative digital mesh, not a working or regulated installation.

Original project asset; redistribution terms for public downloads are not specified.

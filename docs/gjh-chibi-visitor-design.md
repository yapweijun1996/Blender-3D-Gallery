# GJH Chibi Visitor: design reference

Status: the Blender-built model at models/gjh-chibi-visitor/blender/ is the primary gallery entry. The terra, sol, and astra Unity builds remain as earlier experimental comparisons. Exact fidelity to the owner's private character sheet remains unverified.

Source: the owner's “GJH Chibi Visitor, New Design, Modular” character sheet. The sheet image is a private reference and is not embedded here or redistributed.

## Character

Original rounded chibi robot mascot for the GJH mall concept, about two heads tall. Decorative concept, not an official GJH spokesperson.

- Palette: white #F4F2FA, near-black #2A2838, bright purple #8B5CF6, light lavender #D9CCF7.
- Head: large rounded white helmet; two tall, pointed ear-fins swept slightly back; black glossy face screen with glowing purple happy-arc eyes; round ring headphones with a glowing purple ring on each side.
- Body: soft white hoodie with a purple hood roll and a purple GJH mark on the chest; short sleeves with purple panel stripes; black shorts with purple hem; white legs with purple square patches; black rounded mitts and shoes.
- Views on the sheet: front, side, back.

## Modular system (mix and match)

| Module | Variants |
| --- | --- |
| Head (face expression) | happy ^ ^, sleep - -, excited > <, heart |
| Ears / antennas | headphone ear-cups, ball antennas, wing fins |
| Outfit (body) | white hoodie, black jacket, plain top |
| Accessories | backpack, belt bag, ID badge |

Example combinations on the sheet: goggles, cap, scarf, cat ears.

## Runtime contract (target)

- glTF 2.0 GLB, native metres, +Y up, front +Z, feet at Y=0, about 1.0 m tall.
- Root node GJHChibiVisitor with separate child nodes per module: Head, Face, Expression variants, Ears, Headphones, Outfit, Legs, Hands, Feet.
- Default export shows the happy expression and the white hoodie only.
- No external textures. Emissive purple must survive export.
- Budget: under 15,000 triangles and under 2 MiB (same ceiling as gjh-mall-visitor).

The Blender primary's default GLB exceeds the target triangle budget at 38,628 measured triangles and 694,260 bytes. The source docs explain the outline meshes and include the separately measured module kit.

## Authoring and gallery status

The primary model is generated procedurally in Blender 5.2.3 LTS. Its editable scene, generator, default export, all-modules kit, WebP previews, measured metadata, and reproduction steps are in models/gjh-chibi-visitor/blender/README.md. The private sheet image is not redistributed.

The three earlier comparison builds were generated separately in Unity 6000.0.85f2 with glTFast. Their IDs and asset files remain unchanged; metadata and gallery names identify them as Unity experiments.

The collection is registered in models/catalog.json with the Blender model first and the three Unity comparisons after it. Local admission checks are npm run validate:assets, npm test, and npm run build.

# New Moon Illuminated Shop Sign

![Three-quarter view of a dark-green shop sign with gold New Moon lettering and an illuminated crescent](previews/hero.webp)

A wall-mounted **Mall Fixtures** asset measuring **3.200 m wide × 0.900 m high × 0.350 m deep**. Mount the root at the wall surface and at the desired elevation of the lower trim. Its origin lies halfway across that edge. Blender uses +Z up and −Y forward. The GLBs use +Y up and +Z forward, with the mounting straps touching Z = 0.

| Export | Triangles | File size | Suggested use |
| --- | ---: | ---: | --- |
| [Near GLB](exports/optimized.glb) | 17,018 | 855,436 bytes | Gallery viewer, close-ups and oblique views |
| [Far GLB](exports/far-lod.glb) | 954 | 109,276 bytes | Beyond approximately 15 m |

The consuming scene chooses the LOD. The distance is a starting point for a normal field of view. The near file is registered in the gallery catalog. Both files have one root, `ASSET_NewMoonSign`, with six direct children.

| Node | Parts |
| --- | --- |
| `Frame` | Stepped brass cornice with three actual soffit recesses, mitred face border and projecting lower trim |
| `Panel` | Matte bottle-green face and folded enamel case |
| `Moon_Logo` | Raised brass-edged crescent, backlit amber return and luminous botanical enamel |
| `Letters` | Seven separate bevelled meshes set on one baseline, spelling **New Moon** |
| `Light_Strips` | Three recessed bezels with baffles and three warm cream diffusers |
| `Mounting` | Removable blackened steel back and four keyhole straps. Near detail includes folded flanges and rivets |

The far file preserves these controls. Its logo and inscription each use one flat quad. Their UVs partition a single embedded 1024 × 256 alpha-masked image baked from the near meshes. The other far components use simplified solid geometry.

The procedural brass grain varies metallic roughness around 0.35. The enamel roughness is 0.80. Pale-gold letter faces and brass bevels have separate material slots. The crescent has an original 1024 × 128 botanical texture wrapped along its arc. All runtime images are embedded. Light sources use emissive materials with `KHR_materials_emissive_strength`. The Cycles studio supplies the photographed light spill and optical bloom in the previews. The appearance of those effects in an application depends on its lighting and post-processing.

## Source and reproduction

[generate.py](generate.py) builds the geometry in metres, converts the bundled STIX Two Text Regular outlines to meshes, packs its procedural images, saves the [near Blender scene](sources/new-moon-sign.blend), exports both LODs and renders imported copies of the two GLBs. The four gallery views are hero, front, side and 3q, each delivered as PNG and WebP. Inspection views show the [rear hardware](reports/back.png) and the [far artwork](reports/far-front.png). The reference sheet is owner-supplied visual guidance. The filigree is an original drawing.

From the repository root, use the supplied macOS Blender 5.1.2 launcher. The trailing separator forwards generator arguments.

```sh
DYLD_INSERT_LIBRARIES=/private/tmp/claude-501/-Users-yapweijun--claude-spares-spare-Iu3lC0/26a84d71-25c7-41e6-b903-49317aeebb05/scratchpad/modular/guard.dylib /private/tmp/claude-501/-Users-yapweijun--claude-spares-spare-Iu3lC0/26a84d71-25c7-41e6-b903-49317aeebb05/scratchpad/modular/B/Blender.app/Contents/MacOS/Blender -b -noaudio --python models/new-moon-sign/generate.py --
```

- Default generation replaces the sign source and exports. All model inputs are local.
- Append `--pillow-python /path/to/python` when Pillow is installed in a separate interpreter. The delivered WebPs used Pillow at quality 91, method 6. The script can also use a local cwebp executable.
- Append `--skip-render` for an export-only rebuild.
- Append `--export-source` to open the existing native scene, export its near assembly and rebake its inscription and moon. Far enclosure dimensions and detail levels come from the procedural definitions in the script.

```sh
node models/new-moon-sign/validate.mjs
npm run validate:assets
npm test
npm run build
```

[Validation evidence](reports/checks.json) records the repository commands and binary rebuild checks. The [per-part report](reports/assets.json) measures bounds, dimensions and triangle counts directly from the GLBs. Full Khronos reports are included for [near](reports/khronos.json) and [far](reports/khronos-far.json).

See the [visual comparison](reports/visual-review.json) and [rights notice](LICENSE.md). STIX Two Text ships as an unmodified authoring input under SIL Open Font License 1.1. Its complete license is included with the font.

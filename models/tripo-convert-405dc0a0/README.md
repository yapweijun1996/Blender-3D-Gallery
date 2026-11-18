# Tripo FBX character — 405dc0a0

The gallery previews the original Walk on demand. It plays once and holds the
final pose. Reset restores the initial view and pose. The gallery owner supplied
the Tripo ZIP. The creator, generation inputs, and redistribution terms were
unspecified. The gallery disables the download control.

## Files and provenance

| File | SHA-256 |
| --- | --- |
| `tripo_convert_405dc0a0-5953-4840-91af-c1d285541ecd.zip` (originally `aaa.zip`) | `8d0f08b7e4f63d1a88a0f455e586cd9f41165d7f109af1cb999423b5ec0000b7` |
| `tripo_convert_405dc0a0-5953-4840-91af-c1d285541ecd.fbx` inside the ZIP | `74530fbee1e47479718b80a21ada638f0ebcaef79b71632477e9627945e4290a` |
| `tripo_rgb_47b0b0be-5a92-4f81-a124-809f20dd8d87.jpg` inside the ZIP | `db432f3fb0d254322f91e8619a6e0cb26059d3d1fba48c4ec75deb7c527723a8` |
| `character.blend` | `8b3eeb836118bcc0e2dc650b28a41f06427df7f5e402fc0153199483e0dec6eb` |
| `character.glb` | `ad6b2ffce0f06a5df8617346564ead7b966e839188e27663a50daa0b2bb5988e` |
| `poster.webp` | `bd7ce6bcae79457d678f4dfe57890649e91ca97fcb5b5cc4272b7f7aa1af1eda` |

ZIP integrity passed. The importer allows only the two expected regular-file
paths. The editable Blender 5.1.2 file packs the 4096×4096 source JPEG and
opens with `Armature|walk.001` active and the `walk` NLA track muted. The
saved Action matched the imported key positions and interpolation modes on
all 659 F-Curves. The packed and embedded JPEGs match the source JPEG hash. The
5,138,468-byte GLB contains one textured, skinned scene-root mesh with 39,214
triangles, 65 joints, and a single clip named `walk`, exported in `NLA_TRACKS`
mode. The 600×600 poster is a Blender Cycles render of the editable asset at
source frame 15, encoded with `cwebp -q 86`.

## Inspection and limitations

The FBX imports as one mesh with 19,811 vertices, 19,641 faces, one UV map,
one material, and one 65-bone armature. All vertices have one to four bone
influences, with weight sums from 0.999999955 to 1.000000045. The mesh has
416 boundary edges, which account for all 416 non-manifold edges. The audit
found zero wire edges and zero zero-area faces. Two vertices belong to no
face and are absent from the GLB triangle mesh. The texture exceeds the
project's proposed 2048×2048 target.

The Action spans frames 1–57 at 24 fps. The GLB plays for 2.375 s, including
the leading hold before the first key at 1/24 s. The mesh moves approximately
1.034 m along Blender's negative Y axis. After subtracting mean translation,
corresponding start and end surface vertices differ by up to 0.398 mm
(RMS 0.088 mm). Repeating the original clip would jump back to its starting
position. The source action, skin weights, and triangle surface were retained.
Sampled geometry extends down to Z = −0.018 m. Foot contact, self-intersection,
and deformation across every angle and time remain unverified.

## Reproduce and verify

From the repository root, with Blender 5.1.2 and the installed npm packages:

```sh
blender='/Applications/Blender.app/Contents/MacOS/Blender'
qa_dir=$(mktemp -d)
"$blender" -b --factory-startup --disable-autoexec --python-exit-code 1 --python models/tripo-convert-405dc0a0/export.py
node models/tripo-convert-405dc0a0/validate.mjs
"$blender" -b --factory-startup --disable-autoexec --python-exit-code 1 --python models/tripo-convert-405dc0a0/audit-source.py -- "$qa_dir/source.json"
TRIPO_SOURCE_SAMPLES="$qa_dir/source.json" TRIPO_QA_DIR="$qa_dir" node models/tripo-convert-405dc0a0/browser-check.mjs
npm run validate:assets
npm test
```

Khronos validation reported zero errors and zero warnings. Desktop Chrome
158 and Three.js rendered the actual GLB at source frames 1, 15, 29, 43, and
57. The largest one-way nearest-vertex difference over 19,809 source surface
vertices at each frame was 0.0176 mm. The largest bounds difference was
0.00035 mm. The five front-quarter renderings showed an intact silhouette and
texture. Separate Chrome checks of the viewer component with both GLBs
confirmed no autoplay, playback on request, a held final pose, Reset, and
cleanup for Walk, Run, and Sit. Browser testing was limited to desktop Chrome.

In the local sandbox, the Blender executable failed during Metal detection
and the Playwright Chromium launcher failed during process registration. The
export and audit ran with Blender Foundation's `bpy` 5.1.2 build `ec6e62d40fa9`,
scripting auto-execution disabled, and a temporary guard allowing CPU startup
when no Metal device was exposed. Chrome testing used local file fixtures and
the same pose comparison and viewer code. The documented CLI commands remain
the normal reproduction path on a host where both executables can start.

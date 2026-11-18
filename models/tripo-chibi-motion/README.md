# Tripo Chibi Motion Studio

Open **Interactive Demos → Tripo Chibi Motion Studio** or use `?page=tripo-motion`.
All seven clips repeat in the studio. The timeline pauses playback when scrubbed.
The original Walk travels forward roughly 1.03 m, so it returns visibly to its
starting position on each repeat. Run stays in place.

## Source and checksums

The gallery owner supplied the original Tripo ZIP. Its creator and generation
inputs are unspecified. The license and redistribution terms for the Tripo
outputs are unspecified. The gallery disables asset downloads.
[`tripo-convert-405dc0a0`](../tripo-convert-405dc0a0/README.md)

Tripo generated its official preset Run for this exact character in two CLI tasks.

1. `tripo anim rig` rigged `models/tripo-convert-405dc0a0/character.glb` with
   rig type `biped` and spec `mixamo`. Task
   `0bac2557-531b-49e0-ac32-8ef0a7d2e97a` used 25 credits.
2. `tripo anim retarget --animation preset:run --animate-in-place --out-format fbx`
   produced the [preset FBX](source/tripo-preset-run-b8bd37fe.fbx). Task
   `b8bd37fe-212c-43ad-8762-fa12c730c85b` used 10 credits.

The FBX has a mesh named `tripo_node_405dc0a0`, 65 `mixamorig:` joints, and a
single Action, `Armature|Armature|run`, on frames 1–38 at 30 fps. Its Hips
stay at a fixed horizontal position and have 25.5 mm of vertical travel.

| File | SHA-256 |
| --- | --- |
| Original Tripo ZIP | `8d0f08b7e4f63d1a88a0f455e586cd9f41165d7f109af1cb999423b5ec0000b7` |
| Original `character.glb` | `ad6b2ffce0f06a5df8617346564ead7b966e839188e27663a50daa0b2bb5988e` |
| `source/tripo-preset-run-b8bd37fe.fbx` | `d7c6e38bbe876c6c7efd9108d7d1b998740cc25720782534a7c4bbba5a1978b1` |
| `motion.blend` | `e81f01d1e78186d7800fe0724cce1070a670381e2d22ad4d310703c51e9d88ea` |
| `motion.glb` | `ffccda1ba2a50eb10948853e03d17f0d095cd9b953d644c03c4fb9cb95529410` |
| `poster.webp` | `5258212304d257ea89f5216e2e6e06576772ee0a57ea27eafd8934ed6b50bec6` |
| `review/poses-run.webp` | `37262fbe5dd882377f988cf8e2a25a3d03adf21acaad9a1c66d32fe4fbd7e575` |

`export.py` reuses the original importer's exact two-path ZIP allowlist and
regular-file checks. It imports the FBX, packs the 4096 × 4096 source JPEG,
and exports one skinned mesh with 39,214 triangles and the original 65-joint
`mixamorig:` rig. Blender opens `motion.blend` with Idle active and the export
NLA tracks muted. To edit a clip, select its Action on the armature and set the
timeline to its key range. Walk is saved under its original Action name,
`Armature|walk.001`. Run is editable as `run_in_place`.

## Clips

| GLB name | Duration | Pose design |
| --- | ---: | --- |
| `idle` | 3.67 s | Gentle chest movement, sway and head counter-tilt |
| `wave` | 2.67 s | Right-hand greeting with elbow and wrist motion |
| `nod` | 2.33 s | Two nods with a small chest follow-through |
| `jump` | 2.08 s | Crouch, takeoff, 0.22 m peak clearance and landing |
| `dance` | 2.67 s | Alternating weight shifts, torso twist and arm accents |
| `run` | 1.25 s | Tripo's official preset Run, transferred to the original rig as an in-place loop |
| `walk` | 2.38 s | Original forward walk and timing |

`poses.py` defines the five hand-keyed Actions at 24 fps. They use joint
rotations and vertical Hips movement, and foot heights are aligned using the
evaluated skin at authored contact poses.

Tripo supplied the Run motion and a matching joint hierarchy with different
rest axes. For example, the Hips rest axes differ by 90°. `export.py` converts
each bone's local rotation between the rigs' rest bases and saves only the
transferred animation on the original mesh, weights and armature. It samples
the 37 source intervals (1.233 s) by elapsed time across 30 intervals at 24 fps
(1.250 s, the nearest whole-frame duration).

The original Run endpoints differ by up to 28.2° in joint rotation and 9.6 mm
in Hips height. A smoothstep blend over the final three output frame intervals
(0.125 s) brings the pose back to the first key. The horizontal Hips anchor is
the original rig's bind position. The vertical transfer preserves bounce and
uses the source sole clearance relative to its contact level (about 10 mm
below zero) to preserve flight. The exported skin is grounded per sample with
a 1.5 mm margin for interpolation. The rig has no foot-lock IK, collision
solver, or secondary hair simulation. Some foot sliding and contact variation
between keys are possible.

## Reproduce and review

Run from the repository root with Blender 5.1.2 and the repository's installed
npm packages.

```sh
blender -b --factory-startup --disable-autoexec --python-exit-code 1 --python models/tripo-chibi-motion/export.py
node models/tripo-chibi-motion/validate.mjs
npm run validate:assets
npm test
npm run dev
```

On the local Apple Silicon Mac, `blender -b` crashed during Metal detection.
The earlier export used the official `bpy` 5.1.2 CPython 3.13 wheel (build
`ec6e62d40fa9`, wheel SHA-256
`2b3db49cf68f3b1fe931228f34e24fe5325288921a2f4c3192e9ed22aa79d865`).
A process-local temporary dylib guarded the null string encountered while
probing Metal, allowing CPU startup. With the verified wheel installed for
the Python 3.13 interpreter, the fallback can be reproduced as follows.

```sh
motion_work=$(mktemp -d)
cat > "$motion_work/metal-null-guard.c" <<'C'
#include <string.h>
static char *guarded_strstr(const char *haystack, const char *needle)
{
    return haystack == NULL ? NULL : strstr(haystack, needle);
}
__attribute__((used, section("__DATA,__interpose")))
static const struct { const void *replacement; const void *original; }
guard = { (const void *)guarded_strstr, (const void *)strstr };
C
clang -dynamiclib "$motion_work/metal-null-guard.c" -o "$motion_work/metal-null-guard.dylib"
DYLD_INSERT_LIBRARIES="$motion_work/metal-null-guard.dylib" python3.13 -B -c '
import bpy, runpy, sys
bpy.context.preferences.filepaths.use_scripts_auto_execute = False
runpy.run_path(sys.argv[1], run_name="__main__")
' models/tripo-chibi-motion/export.py
```

The preset Run export used the installed Blender 5.1.2 app with the same build
hash and Metal guard. To reproduce that route, run the following after building
the guard above.

```sh
motion_app=/Applications/Blender.app
mkdir -p "$motion_work/Blender.app/Contents/MacOS"
cp "$motion_app/Contents/MacOS/Blender" "$motion_work/Blender.app/Contents/MacOS/"
ln -s "$motion_app/Contents/Resources" "$motion_work/Blender.app/Contents/Resources"
motion_blender="$motion_work/Blender.app/Contents/MacOS/Blender"
codesign --force --sign - "$motion_blender"
DYLD_INSERT_LIBRARIES="$motion_work/metal-null-guard.dylib" "$motion_blender" \
  -b --factory-startup --disable-autoexec --python-exit-code 1 \
  --python models/tripo-chibi-motion/export.py
```

`validate.mjs` checks Khronos validation, rig and clip counts, byte-identical
channels for the five hand-keyed clips and Walk, endpoint equality and zero
horizontal Hips drift for each stationary clip, and 24 fps timing and vertical
bounce for Run. The reopened Blender file retains all 659 original Walk
F-Curves, including key coordinates, handles and interpolation.

The [review directory](review/) contains front-quarter and side views
rendered by Chrome and Three.js from the exported GLB. The preset Run sheet
shows 12 evenly spaced poses per view, from 0 to 1.146 s at roughly 0.104 s
intervals. Chrome 158 and Three.js r187 rendered it with fixed orthographic
cameras. In 240 Three.js samples, the lowest skin point ranged from −3.52 to
16.66 mm relative to the floor, with stance samples between −3.52 and
3.78 mm. Visual review of both views found a recognizable alternating stride
with intact hair and skin and no visible limb penetration in the sampled
poses. The sheet and the reviewed GLB are identified by the checksums above.
[Run pose sheet](review/poses-run.webp)

The Run control at `?page=tripo-motion` loaded the reviewed GLB, scrubbed,
paused, resumed and looped in Chrome with zero console errors.
The other sheets show four poses per clip. The 600 × 600 poster uses Wave at
1.08 s. The existing desktop and mobile screenshots cover the Demos card and
Studio at 1440 × 900 and 390 × 844 CSS pixels and predate the Run replacement.
Pose and floor checks are sampled. Continuous collision checks, physical
devices and other browser engines remain unverified.

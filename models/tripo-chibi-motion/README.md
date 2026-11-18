# Tripo Chibi Motion Studio

Open **Interactive Demos → Tripo Chibi Motion Studio** or use `?page=tripo-motion`.
All seven clips repeat in the studio. The timeline pauses playback when scrubbed.
The original Walk travels forward roughly 1.03 m, so it returns visibly to its
starting position on each repeat. Run stays in place.

## Source and checksums

The gallery owner supplied the Tripo ZIP in
[`../tripo-convert-405dc0a0/`](../tripo-convert-405dc0a0/README.md). The creator,
generation inputs, and redistribution terms are unspecified. The gallery
disables asset downloads.

| File | SHA-256 |
| --- | --- |
| Original Tripo ZIP | `8d0f08b7e4f63d1a88a0f455e586cd9f41165d7f109af1cb999423b5ec0000b7` |
| Original `character.glb` | `ad6b2ffce0f06a5df8617346564ead7b966e839188e27663a50daa0b2bb5988e` |
| `motion.blend` | `76610bf619a4e5584f10ae9e92b028ebe3553672037f05120e83d64134d905a8` |
| `motion.glb` | `576c935b4cb17571bd8463b8bbec988bbec6221d39aa7ed5746d97360827a3bb` |
| `poster.webp` | `5258212304d257ea89f5216e2e6e06576772ee0a57ea27eafd8934ed6b50bec6` |

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
| `run` | 1.00 s | In-place jog with forward lean, bent opposing arms, high knee drive and two flight phases |
| `walk` | 2.38 s | Original forward walk and timing |

`poses.py` defines the six new Actions at 24 fps. They use joint rotations and
vertical Hips movement. Each returns to its first pose with no horizontal
root drift. Foot heights are aligned at authored contact poses using the
evaluated skin. Run has a pose key every three frames. Its two steps are
half a cycle apart, with Hips height adjusted on each exported stance frame
between contact and push-off. The rig has no foot-lock IK, collision solver,
or secondary hair simulation. Foot sliding or contact variation between
exported frames is possible.

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
The export used the official `bpy` 5.1.2 CPython 3.13 wheel (build
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

`validate.mjs` checks Khronos validation, rig and clip counts, every exported
walk channel against the original GLB, and endpoint equality and Hips drift
in the new cycles. The reopened Blender file retains all 659 original Walk
F-Curves, including key coordinates, handles and interpolation.

The [review directory](review/) contains front-quarter and side views
rendered by Chrome and Three.js from the exported GLB. The
[Run sheet](review/poses-run.webp) shows eight poses at 0.125 s intervals,
covering contact, down, passing and flight for both steps. The other sheets
show four poses per clip. The 600 × 600 poster uses Wave at 1.08 s. The desktop and
mobile-width screenshots cover the Demos card and the Studio at 1440 × 900
and 390 × 844 CSS pixels. Chrome switched, paused, scrubbed and looped all
seven clips at both widths with zero console errors. The original GJH page
loaded and exercised its four clip controls. Pose review is sampled.
Continuous collision checks, physical devices and other browser engines
were outside this check.

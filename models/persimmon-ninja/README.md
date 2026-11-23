# Persimmon Scout

An original chibi ninja modeled in Blender 5.1.2. A persimmon and two leaves mark the jade headband. The asymmetric bun, orange scarf and indigo wrap tunic distinguish the figure from each side. The visual brief draws on the exaggerated proportions of the web game *Pockie Ninja* ([developer interview](https://web.17173.com/content/2010-08-23/20100823093911349.shtml)). The figure uses original geometry and materials.

Open [the editable Blender scene](sources/persimmon-ninja.blend) to adjust the named parts. Select **Face expressions**, open **Object Data Properties → Shape Keys**, and adjust **smile**, **surprised** or **blink**. Zero is neutral. Play the timeline to preview **Lookout Idle**. The 13-joint armature uses rigid part weights for a toy-like figure. Extreme poses may show seams at the limb joints.

[The GLB](exports/persimmon-ninja.glb) contains the figure and the idle action. The Blender scene includes the display plinth, portrait camera and lights. The character faces −Y in Blender and +Z in the GLB.

From the repository root, with Blender 5.1.2 and the repository's npm dependencies installed:

```sh
blender --background --factory-startup --disable-autoexec --python-exit-code 1 --python models/persimmon-ninja/generate.py
node models/persimmon-ninja/verification/check.mjs
```

The generator uses geometry helpers from `models/chibi-mall-guide-v5/kit.py`. Set `NINJA_OUT` to rebuild into another directory. The verifier checks the standard export path. It loads the exact GLB in Three.js using Chromium, inspects the skin, expression and animation data, and saves [four views](verification/three-views.png) and a [report](verification/report.json). [Blender portrait](previews/portrait.png).

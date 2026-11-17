# Indigo Ninja head

An original, static chibi portrait for local art review. The design uses swept indigo locks, raised and lowered brows, a sidelong amber gaze, a twin-stroke brass clasp and a stitched vermilion scarf. The blue-haired figure at the lower right of the supplied *Pocket Ninja* ensemble poster informed the silhouette and attitude. The portrait, clasp and back of the head are original interpretations. The poster provides one small oblique face, with no calibrated profile or rear view. No part of the reference models or artwork was imported into the deliverable.

[Editable Blender master](sources/indigo-ninja-head.blend) · [Portable GLB](exports/indigo-ninja-head.glb) · [Studio portrait](previews/hero.png) · [Front](previews/runtime/front.png) · [Profile](previews/runtime/profile.png) · [Back](previews/runtime/back.png)

## Open and edit

Open the master in Blender 5.1.2. The saved camera frames the portrait. Use Numpad 3 for the side and Numpad 0 to return to the camera. The three numbered collections contain the face/scarf, hair, and headband.

Each visible lock is an editable subdivision cage. For a longer sweep, enable **Indigo | editable hair spines** in the Outliner, edit a Bezier point, return to Object Mode, select the guide and run the packed Text Editor script **INSTRUCTIONS - Refresh hair guides.py**. Its width and depth are independent custom properties on the guide. Refresh replaces the selected guide's visible cage, so choose guide edits or direct cage edits for a given lock. Disable the guide collection once finished. Save the edited master as a separate file.

To export the saved edits, from the repository root with Blender available as `blender`:

```sh
blender --background --factory-startup --disable-autoexec /path/to/edited.blend \
  --python-exit-code 1 --python models/indigo-ninja-head/export_source.py -- /path/to/edited.glb
```

## Rebuild and inspect

Run the generator in a separate Blender process. `INDIGO_OUTPUT` can point to a fresh directory to preserve previous outputs. The Blender Lab MCP bridge on this Mac launched the build using the connected app's `bpy.app.binary_path`; the live Classic Visitor scene stayed open. The bridge's separate CLI helper initially failed to locate `blender` on PATH.

```sh
blender --background --factory-startup --disable-autoexec --python-exit-code 1 \
  --python models/indigo-ninja-head/build.py
node models/indigo-ninja-head/qa/check.mjs
blender --background --factory-startup --disable-autoexec \
  models/indigo-ninja-head/sources/indigo-ninja-head.blend --python-exit-code 1 \
  --python models/indigo-ninja-head/verify_edit.py
```

The browser check uses the repository's installed Node dependencies and Chrome. The source edit test uses a temporary export, moves one guide tip in memory, refreshes its lock and verifies that its neighbour and the saved master remain intact. Its output and the browser report identify the tested GLB by SHA-256. [Source edit evidence](qa/editability.json) · [GLB and browser evidence](qa/report.json)

## Art review

The first GLB passed format validation. In its fixed side and back views, separated clumps stood out against a bare cap, and a sharp red patch broke the scarf seam. The front view showed a gentler, more centered expression. The repair joined the top hair with a continuous swept foundation, extended overlapping clumps from crown to nape, shifted both irises together and built the scarf lip into one continuous surface. The reviewer compared the same camera angles after the changes. [First front](qa/round-01/front.png) · [First profile](qa/round-01/profile.png) · [First back](qa/round-01/back.png) · [Final three-quarter view](previews/runtime/three-quarter.png)

The second export still showed a horizontal shelf between the upper crown and the lower locks. The final revision lays the nape control points along the actual crown surface, staggers their angles, and uses fewer samples along the smooth curves. The resulting 67,414 triangles compare with 75,334 in the second export. The final 1,144,052-byte GLB passed Khronos validation with zero errors and warnings. Chrome/Three.js drew it in all four views and both thumbnail checks. The twin-stroke mark reads as a gold accent at 100 pixels. [Round two back](qa/round-02/back.png) · [Independent review](qa/review.md) · [Before and after](previews/runtime/round-comparison.jpg) · [100-pixel avatar](previews/runtime/avatar-100.png) · [Silhouette](previews/runtime/silhouette-100.png)

The deliverable is a static head and scarf with material colours. The desktop viewer recorded 86 draw calls. Full-body posing, facial animation, physical-device performance and character likeness to an unobserved turnaround were outside this study. The source screenshot was left outside the repository; its SHA-256 was `847b3da1775f863704c80b4eee03e266fa6f20340b27049a84960f59cc0aa973`. The Ranyi and Hoodling investigations and their primary sources are in the [project's character study](../../docs/blender/chibi-head-study.md).

# Bakery Serving Tongs

A continuous stainless return spring, cherry handles and rounded evergreen pastry cups form a 214.4 mm utensil. Two jaws with rounded gripping ribs rest on the metal pickup tray. The back of the bent spring forms the third bearing area. The modeled pose is fixed.

The glTF coordinates use metres, +Y up and +Z toward the customer. The long axis points from the return bend toward the jaws along +X. Native dimensions are 214.4 × 45.3 × 23.3 mm in length, depth and height. The artist scene preserves the separate spring, grips, pins and tips in three individually editable collections.

| Export | Triangles | Material draws | Bytes |
| --- | ---: | ---: | ---: |
| LOD0 | 4,028 | 4 | 90,032 |
| LOD1 | 2,172 | 4 | 51,624 |
| LOD2 | 828 | 3 | 19,684 |

## Bakery installation

The upper shelf of the existing Kopitiam Toast Display has an exposed strip in front of the toast. Place the tongs at (0, .254, .102) in the rack’s local coordinates with zero rotation. In the shop the rack sits on the 0.97 m staff worktop of the coffee counter. The jaws and spring sit at 1.224 m from the floor. The customer ledge is 84 mm below the tray. The adjacent glazed cabinet presents two shelves to shoppers and opens at its left rear for staff.

The shop regression checks the tray, rack, customer sightlines and original sliding door. It takes the visitor from the entrance to the pickup point and around the counter to the back of the cabinet. Shifting the tongs 102 mm toward the occupied toast row demonstrates the placement conflict. [Shop regression](../../tests/mall-bakery-shop.test.mjs)

## Reproduce

Run from the gallery root with Blender 5.1.2, Node 24 and the project dependencies.

~~~sh
blender -b --python-exit-code 1 --python models/mall-bakery-serving-tongs/generate.py
blender -b --python-exit-code 1 --python models/mall-bakery-serving-tongs/generate.py -- --export-source
blender -b --python-exit-code 1 --python models/mall-bakery-serving-tongs/inspect_source.py
node models/mall-bakery-serving-tongs/verify.mjs
node --test tests/mall-bakery-shop.test.mjs
~~~

The source check reopens the saved scene, reproduces all three export hashes, then edits one tip in a disposable copy and verifies the saved change in its reimported GLB. The asset check validates each GLB with Khronos, measures its envelope and probes the three bearing areas and the open jaws. [Source evidence](reports/source.json) · [GLB evidence](reports/assets.json) · [Rights](LICENSE.md)

A separate check measured 16.48 mm² of tray contact at the spring and 55.75 mm² at each jaw in LOD0. The nearest toast sits 19.35 mm behind the tongs, and their outer edge sits 20.35 mm inside the front of the tray. Chromium rendered the mounted utensil from the inspection camera in both 900 px and 390 px wide viewports. [Independent installation measurements](reports/installation.json)

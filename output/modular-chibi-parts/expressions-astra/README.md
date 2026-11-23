# Chibi body expressions

The GLB opens in neutral. Three relative shape keys and three companion colour maps provide happy, surprised and sad. The body uses one glTF mesh, one primitive, one skin, 65 joints and one standard PBR material. All 9,512 source triangles are present. Each colour map is a 1024 × 1024 sRGB PNG.

[Body GLB](body_expressions.glb) · [Expression controller](expression.js) · [Four-expression contact sheet](contact_sheet.png)

## Three.js 0.187.0

Place `body_expressions.glb`, `expression.js` and the `textures/` directory together. Use the same installed Three.js package for the controller and GLTFLoader.

```js
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { createExpressionController } from './expression.js';

const { scene: character } = await new GLTFLoader().loadAsync(
  new URL('./body_expressions.glb', import.meta.url).href
);
scene.add(character); // The application's THREE.Scene.

const face = await createExpressionController(character);
face.applyExpression('happy'); // For example, from an expression picker.
```

Call `applyExpression(name)` whenever the selection changes. The controller preloads three maps, keeps the embedded neutral map, and updates the weights and `MeshStandardMaterial.map` synchronously. The map uses the GLB's colour space, sampler and UV orientation with `flipY = false`. The controller clones the material per character. An optional second argument accepts the texture directory URL with a trailing slash. Create one controller per character instance. Call `face.dispose()` when removing that character to release the three external maps and restore its original neutral material.

| Selection | Target at weight 1 | Albedo |
| --- | --- | --- |
| neutral | All three weights 0 | Embedded neutral PNG |
| happy | `expr_happy` | `textures/happy.png` |
| surprised | `expr_surprised` | `textures/surprised.png` |
| sad | `expr_sad` | `textures/sad.png` |

The standalone `textures/neutral.png` is byte-identical to the embedded PNG. A GLB viewer with morph sliders alone shows the geometry component. The illustrated eyelids, brows, pupils and mouth require the map switch.

## What the source contains

Each eye has a separate curved surface with **78 distinct positions and 134 triangles** after matching coincident positions to 1 µm. The large brown irises, pupils, whites, catchlights and dark upper rims are painted. There are no separate brow or eyeball-control bones. The nose and mouth belong to the continuous face surface. A small contour supports the nose. The lip area has a shallow change in profile and a painted mouth line. It has no opening or inner-mouth geometry.

| Source region | Distinct positions | Source GLB vertices including seams |
| --- | ---: | ---: |
| Front face envelope | 423 | 506 |
| Both eye and rim regions | 253 | 271 |
| Brow band | 18 | 18 |
| Nose | 18 | 22 |
| Lips and corners | 7 | 12 |
| Cheeks | 58 | 87 |
| Chin and lower jaw | 28 | 42 |

Counts describe overlapping spatial windows. The connected eye surfaces and the eye-and-rim window use different definitions. The latter also includes the surrounding face. In Blender metres, the face envelope uses `abs(x − 0.000722) < 0.158`, `y < −0.075`, and `0.602 < z < 0.838`. The detailed region windows are in [regions.py](source/regions.py).

The maps reuse the original 2048 px Tripo colour texture. Fifteen facial UV charts receive more room in the new atlas. The body occupies the same 557 rows in all four maps. Repacking introduced 46 GPU seam vertices, increasing the vertex buffer from 6,010 to 6,056. The triangle topology and skin joint order match the source. The largest neutral surface-vertex difference from the source is 0.00036 mm.

## Deformation and hair fit

Happy raises the lower lids, cheeks and mouth corners. Surprised raises the brow area, separates the lip region vertically and lowers the chin. Sad lowers the mouth corners and outer brow region. Geometry supplies depth and movement. Paint supplies the closed lash line, eye whites, iris and pupil changes, and the apparent mouth opening.

| Target | Moved GLB vertices | Distinct moved positions | Peak facial travel | Hairline surface travel, conservative upper bound |
| --- | ---: | ---: | ---: | ---: |
| expr_happy | 387 | 333 | 15.024 mm | 1.611 mm |
| expr_surprised | 383 | 324 | 6.925 mm | 1.622 mm |
| expr_sad | 391 | 335 | 5.256 mm | 0.665 mm |

All **5,536 non-face vertices** have an exactly zero POSITION delta in every target. Hairline means the neutral body surface within 16 mm of the actual bob. Its vertices stay fixed. The surface check also bounds motion between vertices by subdividing triangles and using their distance to the hair. The greatest bound is 1.622 mm in any direction, within the 3 mm outward limit. The highest Happy travel is in the eyelid/cheek area.

The exported bob has 1,754 vertices. The shortest rest-pose Euclidean distance from a bob vertex to the body is **5.818 mm in all four expressions**. Both original bob checkers ran against each expression, in rest and in walk, run, wave, jump, idle, nod and dance. They found **0 hair vertices inside and 0 intersecting triangle pairs**. The smallest reported signed clearance in motion is **4.8 mm** during run. The vertex checker samples 12 frames per clip. The triangle checker samples every third integer frame. These are discrete-pose tests. [Geometry measurements](checks/geometry.json) · [Hair checker results](checks/hair.json)

## Verification and expressive limits

- Khronos glTF Validator 2.0.0-dev.3.10 reported **0 errors and 0 warnings**. [Validator report](checks/khronos.json)
- The offline Three.js r187 test parsed the delivered GLB with GLTFLoader, decoded and compared each selected PNG, checked the real SkinnedMesh weights, repeated a selection and restored neutral. This test exercised runtime data and controller behaviour. The supplied images are Blender Cycles renders. Browser GPU output was outside the test. [Three.js report](checks/three.json)
- The 720 × 720 portraits come from a fresh import of the exported asset into Blender with the corresponding map and target selected. All four share a camera and lighting setup. Independent visual review confirmed the four front-view expressions. [Neutral](renders/neutral.png) · [Happy](renders/happy.png) · [Surprised](renders/surprised.png) · [Sad](renders/sad.png) · [Capture hashes](checks/capture.json) · [Visual review](checks/visual.json)

The controller provides four discrete looks. Weights can interpolate geometry, while illustrated features switch in one step. The closed eye retains some of the source socket relief in close-up. The surprised mouth reads as an opening from the front. Side views expose the continuous mouth surface. The asset provides no teeth, tongue mesh, gaze control or speech shapes.

## Rebuild locally

Run these commands from the delivery directory. The wrapper invokes the specified guarded Blender binary, keeps its temporary paths under this directory, and uses Blender's bundled Python and NumPy for authoring, raster painting and rendering. The last command uses the repository's installed Three.js and Khronos validator.

```sh
source/run_blender.sh source/build.py
source/run_blender.sh source/render.py
source/run_blender.sh source/check_asset.py
source/run_blender.sh source/check_hair.py
node source/check_runtime.mjs
```

The build reads `../hand-gestures-astra/round2/base_body.glb` and `../hair-fit-astra/round2/hair_bob_v2.glb`. The motion check also reads the two adjacent bob checker scripts and the repository's `models/tripo-chibi-motion/motion.glb`. Temporary checker blends and render caches live under `.work/`. A clean rebuild reproduced the GLB and all four maps byte for byte. The final GLB has SHA-256 `5a490e0206ccc903703cfa1eca48d13107a60f07368b633f8823c9f6b04d1052`.

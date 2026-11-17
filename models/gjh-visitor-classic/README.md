# GJH Classic Visitor

A 1.30 m modular human chibi based on the supplied classic GJH Virtual Mall visitor. The default look has chestnut swept hair, a white and violet hoodie, cargo shorts, a backpack, and violet court sneakers.

## Open or use the character

Open `GJH-Classic-Visitor.blend` in Blender. Each slot has its own collection. The Hair collection contains individually editable bangs, crown pieces, side locks and nape. Hat and Jeans are disabled in the viewport and render by default. To try jeans in Blender, enable Jeans and disable Shorts, both Leg collections, and both Sock collections. The 27-bone rig has five named NLA tracks. Unmute one track in the NLA Editor to preview it. The file opens at the neutral pose.

For a game or viewer, load `exports/GJH-Classic-Visitor.glb`. It includes the default 38 slots and the five animations. `exports/modules/` contains 40 separately loadable skinned GLBs, including the two optional garments. The manifest lists each file, its slot, driving bones and triangle count. The soles define the model origin. glTF uses metres, positive Y up and positive Z forward.

The head, ears, nose, wrists, palms, fingers and limbs are separate geometry. Eyes, brows, cheek blush and mouth are independent atlas-mapped surfaces fitted to this head. Each finger has its own joint. The default face is the happy expression. For new face artwork edit `face.svg`, rasterize at 1536 by 256 pixels with transparency, and replace `face.png` before rebuilding. Export meshes merge components by slot and simplify covered geometry. The editable Blender source retains the original components.

## Change the outfit in Three.js

Create one wardrobe controller immediately after loading the character. It caches the original skeleton once. It is safe to equip the supplied hat and jeans in either order, remove either item, and re-equip a detached module.

```js
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { createWardrobe } from './wardrobe.mjs';

const loader = new GLTFLoader();
const model = await loader.loadAsync('./exports/GJH-Classic-Visitor.glb');
scene.add(model.scene);
const wardrobe = createWardrobe(model.scene);
const manifest = await (await fetch('./exports/manifest.json')).json();
const jeans = await loader.loadAsync('./exports/modules/Jeans.glb');
wardrobe.equip('Jeans', jeans.scene, manifest.variants.Jeans.hide);
const cap = await loader.loadAsync('./exports/modules/Hat.glb');
wardrobe.equip('Hat', cap.scene);
wardrobe.remove('Jeans');
```

Each module follows the original character's joints and keeps its own inverse bind matrices. Rigid parts such as Hair and Nose follow Head. The optional hat is fitted to the supplied haircut. New parts should preserve the skeleton's rest transforms and use the same model origin. The controller restores covered slots on removal.

## Animation

The clips are `idle`, `walk`, `run`, `sit`, and `stand_up`. Walk and run are in-place cycles. Corresponding forward root speeds are approximately 0.1917 m/s and 0.5813 m/s. The sitting fixture has a 0.14225 m top, with its front edge 0.045 m behind the model origin. Place the seat in the scene and play the sit action forward to reach its endpoint.

## Rebuild and verify

Run these commands from this asset directory in the gallery checkout. Blender 5.1.2 was used for authoring. Node verification uses the checkout's Three.js, glTF Validator and Playwright packages and a local Chrome installation. All model textures are packed in the Blender and GLB files.

```sh
blender -b --factory-startup --python-exit-code 1 -P build.py
node qa_modules.mjs
blender -b --factory-startup --python-exit-code 1 -P qa_motion.py -- exports/GJH-Classic-Visitor.glb qa/motion.json
node qa_browser.mjs
QA_BOARD=1 QA_VIEWS=front,portrait,three-quarter,profile,back,walk,run,sit blender -b --factory-startup --python-exit-code 1 -P render_qa.py
```

See [the QA record](qa/REVIEW.md) for the verified build and scope.

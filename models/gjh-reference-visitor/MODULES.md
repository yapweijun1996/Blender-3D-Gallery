# Modular visitor

The editable master is `sources/gjh-reference-visitor.blend`. The complete animated character is `exports/gjh-reference-visitor-rigged.glb`; `exports/modules/manifest.json` lists the separately exported modules and their bone bindings. The base character uses `extras.partSlot` to identify all meshes belonging to a slot. Module meshes have the same slot metadata. The modules and character use the same model origin (midpoint between the soles), metres, glTF +Y up and +Z forward.

The slots cover the head, hair, left and right eyes, brows, ears, nose and mouth; body, arms, wrists, palms and ten individual fingers; legs, socks, shoes, hoodie, shorts and backpack. `Hat` and `Jeans` are optional variants. Eyes, brows and mouth are UV-textured transparent patches on the face surface, not standalone eyeballs or mouth interiors. Nose and ears are physically separated from the original sculpt. Hiding an ear leaves a visible skin-coloured underlay, so a clean earless head is not yet supported. Each finger has one rigid bone, not individual knuckle joints.

`Hat` and `Jeans` are hidden in the default Blender scene. The supplied jeans replace `Shorts`, `Leg.L`, `Leg.R`, `Sock.L` and `Sock.R`; the shoes remain. The hat is fitted to this hairstyle, not guaranteed to fit arbitrary replacement hair. Default garments can be hidden together by slot; for example all hoodie pieces, cuffs, collar and chest emblem share `Hoodie`.

## Assembly in Three.js

Each module GLB contains its own copy of the same rest skeleton and one or more skinned meshes. This supports slots such as the hoodie and jeans that use more than one bone. After loading both GLBs with `GLTFLoader`, attach the module's scene under the character's model root and remap the module skeleton's named bones to the existing character bones. Keep the inverse bind matrices from the module. The following is the approach exercised by the Node smoke test, assuming both files came from this build and the character is at its original model-space origin:

```js
const bones = new Map();
character.scene.traverse(o => {
  if (o.isBone) bones.set(o.name, o);
});

// Hide the slot on the character before attaching its replacement.
character.scene.traverse(o => {
  if (o.userData.partSlot === slot) o.visible = false;
});

module.scene.traverse(o => {
  if (!o.isSkinnedMesh) return;
  o.skeleton.bones = o.skeleton.bones.map(b => {
    const target = bones.get(b.name);
    if (!target) throw new Error(`Missing bone: ${b.name}`);
    return target;
  });
});
character.scene.add(module.scene);
character.scene.updateMatrixWorld(true);
```

For a multi-slot replacement such as jeans, hide every slot listed in `manifest.json` under `variants`. Restore the original visibility when removing a module. Dispose unloaded geometries, materials and textures according to the host application. Module GLBs contain a skeleton but no animations; the complete character owns the five draft clips. `exports/gjh-visitor-hair.glb` is a separate static hair-only GLB for rigid head attachment, while `exports/modules/hair.glb` follows the same skinned-module contract as other slots.

## QA and limitations

The modular skeleton has 19 bones, including ten finger bones. The 38 slots were tested in Node Three.js against the full character with five sampled frames per clip and an additional head rotation; individual finger isolation was also tested. These tests do not prove continuous motion, foot or seat contact, browser rendering, material ordering or full range-of-motion quality. The sit clip remains draft and may intersect clothing. The body shoulder ends are simplified and need coverage by an appropriate garment. Optional clothing needs fit testing with any new hair or body variant.

The current hair has approximately 8,876 triangles, down from 62,860; the complete default character is approximately 51,543 triangles and 24 materials, above the reference's low-poly target. Hair reference fidelity remains imperfect at the rear and crown. See `qa/modular-rework/` for hash-bound visual and technical results.

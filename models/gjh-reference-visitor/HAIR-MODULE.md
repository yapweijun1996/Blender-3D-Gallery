# Visitor hair module

Two hair exports serve different uses:

- `exports/modules/hair.glb` is a skinned module that uses the same named skeleton as the full character. See `MODULES.md` for re-binding it together with other modules.
- `exports/gjh-visitor-hair.glb` is a static, rigid hair-only mesh. Its vertices are in the character's rest model space with the origin at the midpoint of the soles; it has no skeleton or animation. It is intended to be attached to the `Head` bone using the inverse rest transform.

For the rigid file, after loading both files with Three.js and before starting animation:

```js
character.scene.updateMatrixWorld(true);
let head;
character.scene.traverse(o => { if (o.isBone && o.name === 'Head') head = o; });
if (!head) throw new Error('Head bone is missing');
const modelToHead = character.scene.matrixWorld.clone().invert().multiply(head.matrixWorld);
character.scene.traverse(o => { if (o.userData.partSlot === 'Hair') o.visible = false; });
head.add(hair.scene);
hair.scene.matrixAutoUpdate = false;
hair.scene.matrix.copy(modelToHead.invert());
```

The character and hair must come from the same build and share the same origin and scale. Do not select the hair node by exact Blender name because Blender may add numeric suffixes; use `partSlot = Hair`, or select the single mesh in the standalone rigid file.

The hair is 8,876 triangles. Source geometry remains editable before the non-destructive Decimate modifier, which precedes the Head armature modifier. The independent hair and the character's hair were verified to coincide at rest, four head rotations and samples of all five draft clips; see `qa/modular-rework/final/hair-animation-v2.json`. The format validator and visual scope are recorded in `qa/modular-rework/REVIEW.md`. The hair still exceeds the reference's budget for the entire character and its rear locks are more regular than the reference.

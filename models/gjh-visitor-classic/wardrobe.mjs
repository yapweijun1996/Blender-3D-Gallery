/** One controller per loaded character scene. Pass a fresh GLTFLoader module scene to equip. */
export function createWardrobe(characterScene) {
  const characterBones = new Map();
  const defaultParts = [];
  const active = new Map();
  characterScene.traverse(node => {
    if (node.isBone) characterBones.set(node.name, node);
    if (node.userData.partSlot) defaultParts.push([node, node.visible]);
  });

  function updateVisibility() {
    const hidden = new Set();
    for (const part of active.values()) {
      for (const slot of part.hideSlots) hidden.add(slot);
    }
    for (const [node, initiallyVisible] of defaultParts) {
      node.visible = initiallyVisible && !hidden.has(node.userData.partSlot);
    }
    for (const [slot, part] of active) {
      const covered = [...active].some(([otherSlot, other]) =>
        otherSlot !== slot && other.hideSlots.has(slot));
      part.scene.visible = part.initiallyVisible && !covered;
    }
    characterScene.updateMatrixWorld(true);
  }

  function remove(slot) {
    const old = active.get(slot);
    if (!old) return;
    old.scene.removeFromParent();
    old.scene.visible = old.initiallyVisible;
    for (const [skeleton, localBones] of old.skeletons) skeleton.bones = localBones;
    active.delete(slot);
    updateVisibility();
  }

  function equip(slot, moduleScene, hideSlots = [slot]) {
    if (active.get(slot)?.scene === moduleScene) return;
    if (moduleScene.parent) throw new Error('The module must be detached before equipping it.');
    const skeletons = new Map();
    const resolved = new Map();
    let slotFound = false;
    moduleScene.traverse(node => {
      if (node.userData.partSlot === slot) slotFound = true;
      if (!node.isSkinnedMesh || skeletons.has(node.skeleton)) return;
      skeletons.set(node.skeleton, node.skeleton.bones);
      resolved.set(node.skeleton, node.skeleton.bones.map(joint => {
        const target = characterBones.get(joint.name);
        if (!target) throw new Error('Unknown character joint ' + joint.name);
        return target;
      }));
    });
    if (!slotFound || !skeletons.size) throw new Error('Invalid module for ' + slot);
    remove(slot);
    for (const [skeleton, bones] of resolved) skeleton.bones = bones;
    active.set(slot, {scene: moduleScene, initiallyVisible: moduleScene.visible,
      skeletons, hideSlots: new Set(hideSlots)});
    characterScene.add(moduleScene);
    updateVisibility();
  }

  return {equip, remove};
}

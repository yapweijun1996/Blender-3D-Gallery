import { Quaternion, SkeletonHelper, Vector3 } from "three";

export function createChibiRigControls({ model, scene, container, invalidate }) {
  const arm = model.getObjectByName("LeftArm");
  const rest = arm.quaternion.clone();
  const axis = new Vector3(0, 0, 1).applyQuaternion(
    arm.parent.getWorldQuaternion(new Quaternion()).invert(),
  );
  const raise = new Quaternion().setFromAxisAngle(axis, Math.PI * 0.32);
  const bones = new SkeletonHelper(model);
  bones.material.depthTest = false;
  bones.renderOrder = 10;
  scene.add(bones);

  const toolbar = document.createElement("div");
  toolbar.className = "vehicle-controls";
  toolbar.setAttribute("role", "group");
  toolbar.setAttribute("aria-label", "Chibi rig controls");
  container.insertAdjacentElement("afterend", toolbar);
  function toggle(label, apply) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "outline-button";
    button.textContent = label;
    toolbar.append(button);
    function set(enabled) {
      button.setAttribute("aria-pressed", String(enabled));
      apply(enabled);
      invalidate();
    }
    button.onclick = () => set(button.getAttribute("aria-pressed") !== "true");
    set(false);
    return set;
  }
  const pose = toggle("Raise left arm", enabled => {
    arm.quaternion.copy(rest);
    if (enabled) arm.quaternion.premultiply(raise);
  });
  const overlay = toggle("Show skeleton", enabled => { bones.visible = enabled; });
  return {
    reset() { pose(false); overlay(false); },
    dispose() {
      toolbar.remove();
      bones.removeFromParent();
      bones.dispose();
      model.traverse(node => { if (node.isSkinnedMesh) node.skeleton.dispose(); });
    },
  };
}

import { MathUtils, Vector3 } from 'three';

export const handoverDuration = 1.18;
export const revealInterval = .23;

export function createLetterFlight(letter, scene) {
  const [left, bottom, right, top] = letter.userData.paperBounds;
  const center = new Vector3((left + right) / 2, (bottom + top) / 2, 0);
  const parent = letter.parent;
  const rest = { position: letter.position.clone(), rotation: letter.quaternion.clone(), scale: letter.scale.clone() };
  const destination = new Vector3(), scale = new Vector3(), centerOffset = new Vector3();
  const projected = new Vector3();
  let startPosition, startRotation;

  function project(camera, viewport) {
    const rect = { left: Infinity, top: Infinity, right: -Infinity, bottom: -Infinity };
    letter.updateWorldMatrix(true, false);
    for (const x of [left, right]) for (const y of [bottom, top]) {
      projected.set(x, y, 0).applyMatrix4(letter.matrixWorld).project(camera);
      const px = viewport.left + (1 + projected.x) * viewport.width / 2;
      const py = viewport.top + (1 - projected.y) * viewport.height / 2;
      rect.left = Math.min(rect.left, px);
      rect.right = Math.max(rect.right, px);
      rect.top = Math.min(rect.top, py);
      rect.bottom = Math.max(rect.bottom, py);
    }
    return rect;
  }

  return {
    begin() {
      scene.attach(letter);
      startPosition = letter.position.clone();
      startRotation = letter.quaternion.clone();
    },
    pose(camera, viewport, stage, time) {
      const width = Math.min(stage.width * .96, 660);
      const height = Math.min(stage.height * .88, Math.max(385, width * .64));
      const x = stage.left + stage.width / 2, y = stage.top + stage.height / 2;
      const depth = Math.min(4.8, camera.position.z * .54);
      destination.set(2 * (x - viewport.left) / viewport.width - 1, 1 - 2 * (y - viewport.top) / viewport.height, .5)
        .unproject(camera);
      camera.worldToLocal(destination);
      destination.multiplyScalar(depth / -destination.z);
      camera.localToWorld(destination);
      const projection = camera.projectionMatrix.elements;
      scale.set(2 * depth * width / (viewport.width * projection[0] * (right - left)),
        2 * depth * height / (viewport.height * projection[5] * (top - bottom)), 1);
      centerOffset.copy(center).multiply(scale).applyQuaternion(camera.quaternion);
      destination.sub(centerOffset);

      const progress = MathUtils.smootherstep(time, 0, handoverDuration);
      letter.position.lerpVectors(startPosition, destination, progress);
      letter.position.y += .13 * Math.sin(Math.PI * progress);
      letter.quaternion.slerpQuaternions(startRotation, camera.quaternion, progress);
      letter.scale.lerpVectors(rest.scale, scale, progress);
      return project(camera, viewport);
    },
    project,
    reset() {
      parent.add(letter);
      letter.position.copy(rest.position);
      letter.quaternion.copy(rest.rotation);
      letter.scale.copy(rest.scale);
      letter.visible = true;
    },
  };
}

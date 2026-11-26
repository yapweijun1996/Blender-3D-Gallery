import { Matrix4 } from 'three';

export function createBoundsRecorder() {
  const worldToClip = new Matrix4(), meshToClip = new Matrix4();
  return (root, camera, viewport) => {
    const bounds = {left: Infinity, top: Infinity, right: -Infinity, bottom: -Infinity};
    const halfWidth = viewport.width / 2, halfHeight = viewport.height / 2;
    const midX = viewport.left + halfWidth, midY = viewport.top + halfHeight;
    worldToClip.multiplyMatrices(camera.projectionMatrix, camera.matrixWorldInverse);
    root.traverseVisible(object => {
      if (!object.isMesh) return;
      const positions = object.geometry.attributes.position;
      // Compute one transform per mesh and project every original vertex.
      const m = meshToClip.multiplyMatrices(worldToClip, object.matrixWorld).elements;
      for (let i = 0; i < positions.count; i++) {
        const x = positions.getX(i), y = positions.getY(i), z = positions.getZ(i);
        const invW = 1 / (m[3] * x + m[7] * y + m[11] * z + m[15]);
        const px = midX + (m[0] * x + m[4] * y + m[8] * z + m[12]) * invW * halfWidth;
        const py = midY - (m[1] * x + m[5] * y + m[9] * z + m[13]) * invW * halfHeight;
        bounds.left = Math.min(bounds.left, px);
        bounds.right = Math.max(bounds.right, px);
        bounds.top = Math.min(bounds.top, py);
        bounds.bottom = Math.max(bounds.bottom, py);
      }
    });
    return bounds;
  };
}

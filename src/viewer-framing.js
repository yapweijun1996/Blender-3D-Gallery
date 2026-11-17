import * as THREE from "three";

const DEFAULT_HEIGHT_FILL = 0.75;
const DEFAULT_WIDTH_FILL = 0.9;

/** Keep the renderer backing size and perspective projection aligned to CSS pixels. */
export function syncViewerSize(container, renderer, camera, pixelRatio = renderer.getPixelRatio()) {
  const { width, height } = container.getBoundingClientRect();
  if (!(width > 0 && height > 0)) {
    return { sizeChanged: false, aspectChanged: false, pixelRatioChanged: false };
  }
  if (!(Number.isFinite(pixelRatio) && pixelRatio > 0)) {
    throw new RangeError("Viewer pixel ratio must be positive and finite");
  }

  const currentSize = renderer.getSize(new THREE.Vector2());
  const sizeChanged = currentSize.x !== width || currentSize.y !== height;
  const aspect = width / height;
  const aspectChanged = camera.aspect !== aspect;
  const pixelRatioChanged = renderer.getPixelRatio() !== pixelRatio;

  if (pixelRatioChanged) renderer.setPixelRatio(pixelRatio);
  if (sizeChanged) renderer.setSize(width, height, false);
  if (aspectChanged) {
    camera.aspect = aspect;
    camera.updateProjectionMatrix();
  }

  return { sizeChanged, aspectChanged, pixelRatioChanged };
}

function fitViewerPoints(
  bounds,
  camera,
  direction,
  options,
  visitPoints,
  pointCount,
) {
  const { heightFill = DEFAULT_HEIGHT_FILL, widthFill = DEFAULT_WIDTH_FILL } = options;
  if (bounds.isEmpty()) throw new RangeError("Cannot frame empty model bounds");
  if (!camera.isPerspectiveCamera) {
    throw new TypeError("The model viewer requires a perspective camera");
  }
  if (!(heightFill > 0 && heightFill < 1) || !(widthFill > 0 && widthFill < 1)) {
    throw new RangeError("Frame fill targets must be between zero and one");
  }

  const center = bounds.getCenter(new THREE.Vector3());
  const viewDirection = direction.clone().normalize();
  if (viewDirection.lengthSq() === 0) {
    throw new RangeError("Camera direction must be non-zero");
  }

  const right = new THREE.Vector3().crossVectors(camera.up, viewDirection);
  if (right.lengthSq() < 1e-12) {
    const fallbackUp = Math.abs(viewDirection.y) < 0.9
      ? new THREE.Vector3(0, 1, 0)
      : new THREE.Vector3(0, 0, 1);
    right.crossVectors(fallbackUp, viewDirection);
  }
  right.normalize();
  const up = new THREE.Vector3().crossVectors(viewDirection, right).normalize();
  const halfVerticalFov = THREE.MathUtils.degToRad(camera.fov / 2);
  const halfHorizontalFov = Math.atan(
    Math.tan(halfVerticalFov) * Math.max(camera.aspect, Number.EPSILON),
  );
  const verticalLimit = Math.tan(halfVerticalFov) * heightFill;
  const horizontalLimit = Math.tan(halfHorizontalFov) * widthFill;
  const projectedPoints = new Float64Array(pointCount * 3);
  const offset = new THREE.Vector3();
  let index = 0;
  let maxDepth = -Infinity;
  visitPoints((point) => {
    offset.copy(point).sub(center);
    projectedPoints[index++] = offset.dot(viewDirection);
    projectedPoints[index++] = offset.dot(right);
    projectedPoints[index++] = offset.dot(up);
    maxDepth = Math.max(maxDepth, projectedPoints[index - 3]);
  });

  const size = bounds.getSize(new THREE.Vector3());
  const radius = Math.max(size.length() / 2, Number.EPSILON);
  const maxRadiusDistance = Math.max(radius * 1.05, maxDepth + radius * 1e-6);
  let distance = maxRadiusDistance;
  for (let point = 0; point < index; point += 3) {
    const depth = projectedPoints[point];
    distance = Math.max(
      distance,
      depth + Math.abs(projectedPoints[point + 2]) / verticalLimit,
      depth + Math.abs(projectedPoints[point + 1]) / horizontalLimit,
    );
  }

  const centeredExtents = (candidateDistance, component, initialTarget = 0) => {
    let target = initialTarget;
    let minIndex = 0;
    let maxIndex = 0;
    let min = -Infinity;
    let max = Infinity;
    for (let iteration = 0; iteration < 3; iteration += 1) {
      min = Infinity;
      max = -Infinity;
      for (let point = 0; point < index; point += 3) {
        const depth = projectedPoints[point];
        const projected = (projectedPoints[point + component] - target) / (candidateDistance - depth);
        if (projected < min) {
          min = projected;
          minIndex = point;
        }
        if (projected > max) {
          max = projected;
          maxIndex = point;
        }
      }
      const minDepth = candidateDistance - projectedPoints[minIndex];
      const maxDepth = candidateDistance - projectedPoints[maxIndex];
      const minWeight = 1 / minDepth;
      const maxWeight = 1 / maxDepth;
      target = (
        projectedPoints[minIndex + component] * minWeight +
        projectedPoints[maxIndex + component] * maxWeight
      ) / (minWeight + maxWeight);
    }

    min = Infinity;
    max = -Infinity;
    for (let point = 0; point < index; point += 3) {
      const projected = (projectedPoints[point + component] - target) /
        (candidateDistance - projectedPoints[point]);
      min = Math.min(min, projected);
      max = Math.max(max, projected);
    }
    return { target, min, max };
  };

  const fitsTargets = (candidateDistance) => {
    const horizontal = centeredExtents(candidateDistance, 1);
    const vertical = centeredExtents(candidateDistance, 2);
    return (
      (horizontal.max - horizontal.min) / (2 * Math.tan(halfHorizontalFov)) <= widthFill &&
      (vertical.max - vertical.min) / (2 * Math.tan(halfVerticalFov)) <= heightFill
    );
  };
  let low = Math.max(maxDepth + Math.max(radius * 1e-6, Number.EPSILON), Number.EPSILON);
  let high = distance;
  while (!fitsTargets(high)) high *= 2;
  for (let iteration = 0; iteration < 24; iteration += 1) {
    const middle = (low + high) / 2;
    if (fitsTargets(middle)) high = middle;
    else low = middle;
  }
  distance = high;
  const horizontal = centeredExtents(distance, 1);
  const vertical = centeredExtents(distance, 2);
  const target = center
    .clone()
    .addScaledVector(right, horizontal.target)
    .addScaledVector(up, vertical.target);

  return {
    center,
    target,
    direction: viewDirection,
    distance,
    radius,
    minDistance: Math.max(radius * 0.05, distance * 0.18),
    maxDistance: Math.max(distance * 12, radius * 12),
  };
}

/** Fit a perspective camera around every corner of a world-space box. */
export function fitViewerBounds(bounds, camera, direction, options = {}) {
  return fitViewerPoints(bounds, camera, direction, options, (visit) => {
    for (const x of [bounds.min.x, bounds.max.x]) {
      for (const y of [bounds.min.y, bounds.max.y]) {
        for (const z of [bounds.min.z, bounds.max.z]) {
          visit(new THREE.Vector3(x, y, z));
        }
      }
    }
  }, 8);
}

/** Fit visible, transformed mesh vertices so sparse bounds do not waste space. */
export function fitViewerObject(object, camera, direction, options = {}) {
  object.updateWorldMatrix(true, true);
  const bounds = new THREE.Box3();
  let pointCount = 0;
  const forEachVertex = (visit) => {
    const local = new THREE.Vector3();
    const world = new THREE.Vector3();
    const instance = new THREE.Matrix4();
    const matrix = new THREE.Matrix4();
    object.traverse((node) => {
      if (!node.isMesh || !node.geometry?.getAttribute("position")) return;
      for (let parent = node; parent; parent = parent.parent) {
        if (!parent.visible) return;
        if (parent === object) break;
      }
      if (node.isSkinnedMesh) node.skeleton.update();
      const position = node.geometry.getAttribute("position");
      const instances = node.isInstancedMesh ? node.count : 1;
      for (let instanceIndex = 0; instanceIndex < instances; instanceIndex += 1) {
        if (node.isInstancedMesh) {
          node.getMatrixAt(instanceIndex, instance);
          matrix.multiplyMatrices(node.matrixWorld, instance);
        } else {
          matrix.copy(node.matrixWorld);
        }
        for (let index = 0; index < position.count; index += 1) {
          node.getVertexPosition(index, local);
          world.copy(local).applyMatrix4(matrix);
          if (!Number.isFinite(world.x + world.y + world.z)) continue;
          visit(world);
        }
      }
    });
  };

  forEachVertex((point) => {
    bounds.expandByPoint(point);
    pointCount += 1;
  });
  if (bounds.isEmpty()) bounds.setFromObject(object);
  const visitPoints = (visit) => {
    if (bounds.isEmpty()) return;
    let foundVertex = false;
    forEachVertex((point) => {
      foundVertex = true;
      visit(point);
    });
    if (foundVertex) return;
    pointCount = 8;
    for (const x of [bounds.min.x, bounds.max.x]) {
      for (const y of [bounds.min.y, bounds.max.y]) {
        for (const z of [bounds.min.z, bounds.max.z]) {
          visit(new THREE.Vector3(x, y, z));
        }
      }
    }
  };
  return fitViewerPoints(bounds, camera, direction, options, visitPoints, pointCount || 8);
}

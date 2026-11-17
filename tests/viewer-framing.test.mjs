import test from "node:test";
import assert from "node:assert/strict";
import { Box3, CylinderGeometry, Mesh, PerspectiveCamera, Vector3 } from "three";
import { fitViewerBounds, fitViewerObject, syncViewerSize } from "../src/viewer-framing.js";

const direction = new Vector3(1, 0.9, 1).normalize();

function projectedBounds(bounds, camera, fit) {
  camera.position.copy(fit.target).addScaledVector(fit.direction, fit.distance);
  camera.lookAt(fit.target);
  camera.updateMatrixWorld(true);
  const min = new Vector3(Infinity, Infinity, Infinity);
  const max = new Vector3(-Infinity, -Infinity, -Infinity);
  for (const x of [bounds.min.x, bounds.max.x]) {
    for (const y of [bounds.min.y, bounds.max.y]) {
      for (const z of [bounds.min.z, bounds.max.z]) {
        const point = new Vector3(x, y, z).project(camera);
        min.min(point);
        max.max(point);
      }
    }
  }
  return { min, max };
}

function projectedObjectVertices(object, camera, fit) {
  camera.position.copy(fit.target).addScaledVector(fit.direction, fit.distance);
  camera.lookAt(fit.target);
  camera.updateMatrixWorld(true);
  object.updateWorldMatrix(true, true);
  const min = new Vector3(Infinity, Infinity, Infinity);
  const max = new Vector3(-Infinity, -Infinity, -Infinity);
  object.traverse((node) => {
    if (!node.isMesh) return;
    if (node.isSkinnedMesh) node.skeleton.update();
    const position = node.geometry.getAttribute("position");
    const vertex = new Vector3();
    for (let index = 0; index < position.count; index += 1) {
      const point = node.getVertexPosition(index, vertex).applyMatrix4(node.matrixWorld).project(camera);
      min.min(point);
      max.max(point);
    }
  });
  return { min, max };
}

const shapes = [
  { name: "character", size: [0.65, 2.1, 0.48] },
  { name: "tall rack", size: [1.2, 4.8, 0.9] },
  { name: "wide platform", size: [12, 1.2, 8] },
  { name: "piano", size: [2.4, 1.1, 1.8] },
  { name: "tiny object", size: [0.0004, 0.0008, 0.0003] },
  { name: "huge structure", size: [240, 92, 160] },
];

test("viewer framing fits model bounds across desktop and mobile aspect ratios", () => {
  for (const { name, size } of shapes) {
    const half = new Vector3(...size).multiplyScalar(0.5);
    const bounds = new Box3(half.clone().negate(), half);
    for (const aspect of [1440 / 900, 390 / 371]) {
      const camera = new PerspectiveCamera(35, aspect, 0.001, 1000);
      const fit = fitViewerBounds(bounds, camera, direction);
      camera.near = Math.max(fit.radius * 0.001, Number.EPSILON);
      camera.far = Math.max(fit.radius * 50, fit.distance * 12 + fit.radius);
      camera.updateProjectionMatrix();
      const projected = projectedBounds(bounds, camera, fit);
      assert.ok(projected.min.x >= -0.901 && projected.max.x <= 0.901,
        `${name} stays within the horizontal margin at aspect ${aspect}`);
      assert.ok(projected.min.y >= -0.751 && projected.max.y <= 0.751,
        `${name} stays within the vertical margin at aspect ${aspect}`);
      assert.ok(projected.min.z > -1 && projected.max.z < 1,
        `${name} stays between the camera clipping planes`);
      assert.ok(fit.minDistance > 0 && fit.minDistance < fit.distance,
        `${name} can still zoom closer than its reset distance`);
      assert.ok(fit.maxDistance > fit.distance,
        `${name} can still zoom farther than its reset distance`);
      if (name === "character" || name === "tiny object") {
        const verticalFill = (projected.max.y - projected.min.y) / 2;
        assert.ok(verticalFill >= 0.7 && verticalFill <= 0.76,
          `${name} fills about three quarters of the viewport height`);
      }
    }
  }
});

test("viewer resize keeps projection and renderer dimensions aligned, then refits", () => {
  let width = 1;
  let height = 1;
  let pixelRatio = 1;
  const renderer = {
    domElement: { width: 1, height: 1 },
    getPixelRatio: () => pixelRatio,
    getSize: target => target.set(width, height),
    setPixelRatio(value) {
      pixelRatio = value;
      this.domElement.width = Math.floor(width * pixelRatio);
      this.domElement.height = Math.floor(height * pixelRatio);
    },
    setSize(nextWidth, nextHeight) {
      width = nextWidth;
      height = nextHeight;
      this.domElement.width = Math.floor(width * pixelRatio);
      this.domElement.height = Math.floor(height * pixelRatio);
    },
  };
  const camera = new PerspectiveCamera(35, 1, 0.001, 1000);
  const dimensions = [
    [1058, 495, 1],
    [960, 330, 2],
    [190, 81, 1],
    [350, 371.359375, 2],
  ];

  for (const [nextWidth, nextHeight, nextPixelRatio] of dimensions) {
    const container = {
      getBoundingClientRect: () => ({ width: nextWidth, height: nextHeight }),
    };
    const change = syncViewerSize(container, renderer, camera, nextPixelRatio);
    const aspect = nextWidth / nextHeight;
    assert.equal(width, nextWidth);
    assert.equal(height, nextHeight);
    assert.equal(camera.aspect, aspect);
    assert.equal(renderer.domElement.width, Math.floor(nextWidth * nextPixelRatio));
    assert.equal(renderer.domElement.height, Math.floor(nextHeight * nextPixelRatio));
    assert.ok(change.sizeChanged || change.aspectChanged || change.pixelRatioChanged);

    const half = new Vector3(0.325, 1.05, 0.24);
    const bounds = new Box3(half.clone().negate(), half);
    const fit = fitViewerBounds(bounds, camera, direction);
    const projected = projectedBounds(bounds, camera, fit);
    assert.ok(projected.min.x >= -0.901 && projected.max.x <= 0.901,
      `the model stays inside the renderer width at aspect ${aspect}`);
    assert.ok(projected.min.y >= -0.751 && projected.max.y <= 0.751,
      `the model stays inside the renderer height at aspect ${aspect}`);
    assert.ok(Math.abs(projected.min.x + projected.max.x) < 0.02,
      `the model remains horizontally centered at aspect ${aspect}`);
    assert.ok(Math.abs(projected.min.y + projected.max.y) < 0.02,
      `the model remains vertically centered at aspect ${aspect}`);
  }

  const unchanged = syncViewerSize({
    getBoundingClientRect: () => ({ width, height }),
  }, renderer, camera, pixelRatio);
  assert.deepEqual(unchanged, {
    sizeChanged: false,
    aspectChanged: false,
    pixelRatioChanged: false,
  });
  const hidden = syncViewerSize({
    getBoundingClientRect: () => ({ width: 0, height: 0 }),
  }, renderer, camera, pixelRatio);
  assert.deepEqual(hidden, {
    sizeChanged: false,
    aspectChanged: false,
    pixelRatioChanged: false,
  });
});

test("viewer framing rejects invalid boxes, cameras, and directions", () => {
  const camera = new PerspectiveCamera(35, 1, 0.001, 1000);
  const bounds = new Box3(new Vector3(-1, -1, -1), new Vector3(1, 1, 1));
  assert.throws(() => fitViewerBounds(new Box3(), camera, direction), /empty model bounds/);
  assert.throws(() => fitViewerBounds(bounds, camera, new Vector3()), /non-zero/);
  assert.throws(() => fitViewerBounds(bounds, {}, direction), /perspective camera/);
  assert.throws(() => fitViewerBounds(bounds, camera, direction, { heightFill: 1 }), /between zero and one/);
});

test("viewer framing uses transformed geometry vertices instead of empty box corners", () => {
  const mesh = new Mesh(new CylinderGeometry(0.45, 0.75, 2.4, 12, 2));
  mesh.position.set(3, 5, -2);
  mesh.rotation.set(0.12, 0.31, -0.08);
  const camera = new PerspectiveCamera(35, 1440 / 900, 0.001, 1000);
  const fit = fitViewerObject(mesh, camera, direction);
  const repeatedFit = fitViewerObject(mesh, camera, direction);
  assert.equal(repeatedFit.distance, fit.distance);
  assert.deepEqual(repeatedFit.target.toArray(), fit.target.toArray());
  camera.near = Math.max(fit.radius * 0.001, Number.EPSILON);
  camera.far = Math.max(fit.radius * 50, fit.distance * 12 + fit.radius);
  camera.updateProjectionMatrix();
  const projected = projectedObjectVertices(mesh, camera, fit);
  assert.ok(projected.min.x >= -0.901 && projected.max.x <= 0.901);
  assert.ok(projected.min.y >= -0.751 && projected.max.y <= 0.751);
  const verticalFill = (projected.max.y - projected.min.y) / 2;
  assert.ok(verticalFill >= 0.7 && verticalFill <= 0.76,
    "the visible mesh fills about three quarters of the viewport height");
});

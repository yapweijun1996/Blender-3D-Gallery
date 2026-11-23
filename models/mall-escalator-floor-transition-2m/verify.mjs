import assert from 'node:assert/strict';
import fs from 'node:fs';
import { createHash } from 'node:crypto';
import { Box3, Raycaster, Vector3 } from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import validator from 'gltf-validator';

const slug = 'mall-escalator-floor-transition-2m';
const file = (name) => new URL(name, import.meta.url);
const hash = (bytes) => createHash('sha256').update(bytes).digest('hex');
const metadata = JSON.parse(fs.readFileSync(file('metadata.json')));

function assertClose(actual, expected, tolerance = 0.000001) {
  assert.ok(
    Number.isFinite(actual) && Math.abs(actual - expected) <= tolerance,
    actual + ' differs from ' + expected,
  );
}

function inspectTopology(root) {
  const vertices = new Map();
  const edgeDirections = new Map();
  const neighbours = [];
  let signedVolume = 0;
  let triangles = 0;
  let draws = 0;

  function vertexId(point) {
    // glTF material primitives may duplicate vertices along a shared physical edge.
    const key = point
      .toArray()
      .map((value) => Math.round(value * 1e7))
      .join('/');
    if (!vertices.has(key)) {
      vertices.set(key, vertices.size);
      neighbours.push(new Set());
    }
    return vertices.get(key);
  }

  root.traverse((mesh) => {
    if (!mesh.isMesh) return;
    draws++;
    const positions = mesh.geometry.getAttribute('position');
    const index = mesh.geometry.index;
    const count = index?.count ?? positions.count;
    for (let start = 0; start < count; start += 3) {
      const corners = [];
      for (let corner = start; corner < start + 3; corner++) {
        const positionIndex = index ? index.getX(corner) : corner;
        const point = new Vector3().fromBufferAttribute(
          positions,
          positionIndex,
        );
        corners.push(point.applyMatrix4(mesh.matrixWorld));
      }
      const [a, b, c] = corners;
      const ab = b.clone().sub(a);
      const ac = c.clone().sub(a);
      assert.ok(ab.cross(ac).length() > 1e-10, 'zero-area triangle');
      const ids = corners.map(vertexId);
      for (let side = 0; side < 3; side++) {
        const from = ids[side];
        const to = ids[(side + 1) % 3];
        const key = Math.min(from, to) + '/' + Math.max(from, to);
        const directions = edgeDirections.get(key) ?? [];
        directions.push(from < to ? 1 : -1);
        edgeDirections.set(key, directions);
        neighbours[from].add(to);
        neighbours[to].add(from);
      }
      signedVolume += a.dot(b.clone().cross(c)) / 6;
      triangles++;
    }
  });

  for (const directions of edgeDirections.values()) {
    assert.ok(
      directions.length === 2 && directions[0] + directions[1] === 0,
      'unpaired or reversed manifold edge',
    );
  }
  const visited = new Set();
  const pending = [0];
  while (pending.length) {
    const current = pending.pop();
    if (visited.has(current)) continue;
    visited.add(current);
    for (const neighbour of neighbours[current]) {
      if (!visited.has(neighbour)) pending.push(neighbour);
    }
  }
  assert.equal(visited.size, vertices.size, 'single connected solid');
  assert.equal(
    vertices.size - edgeDirections.size + triangles,
    2,
    'genus-zero closed shell',
  );
  const slabVolume = 2 * 0.12 * 0.1;
  const recessVolume = 1.56 * 0.025 * 0.085;
  assertClose(signedVolume, slabVolume - recessVolume, 0.0000006);
  return {
    triangles,
    draws,
    weldedVertices: vertices.size,
    undirectedEdges: edgeDirections.size,
    signedVolume,
  };
}

function checkWalkingSurface(cast) {
  let topRays = 0;
  for (let column = 0; column <= 100; column++) {
    const x = -0.99998 + (column * 1.99996) / 100;
    for (let row = 0; row <= 18; row++) {
      const z = 0.00001 + (row * 0.11998) / 18;
      const hit = cast([x, 0.035, z], [0, -1, 0]);
      assertClose(hit?.point.y, 0);
      topRays++;
    }
  }
  const traction = cast([0.046, 0.04, 0.036], [0, -1, 0]);
  const steel = cast([0.046, 0.04, 0.096], [0, -1, 0]);
  assert.equal(traction?.object.material.name, 'Graphite traction inlay');
  assert.equal(steel?.object.material.name, 'Brushed terminal steel');
  return topRays;
}

function checkRecess(cast) {
  const samplesX = [
    -0.994, -0.9, -0.781, -0.777, -0.64, 0.01, 0.64, 0.777, 0.781, 0.9, 0.994,
  ];
  for (const x of samplesX) {
    for (const z of [0.0003, 0.0101, 0.0248, 0.0252, 0.1198]) {
      const insideRecess = Math.abs(x) < 0.78 && z < 0.025;
      const underside = cast([x, -0.17, z], [0, 1, 0]);
      assertClose(underside?.point.y, insideRecess ? -0.015 : -0.1);
    }
  }
  const backWall = cast([0.000003, -0.049, -0.01], [0, 0, 1]);
  assertClose(backWall?.point.z, 0.025);
}

function checkShoulders(cast, levelIndex) {
  for (const side of [-1, 1]) {
    const pocketSide = cast([side * 0.774, -0.05, 0.011], [side, 0, 0]);
    const outsideEdge = cast([side * 1.1, -0.049, 0.006], [-side, 0, 0]);
    assertClose(pocketSide?.point.x, side * 0.78);
    assertClose(outsideEdge?.point.x, side);

    const plateRows = [
      [-0.007, [0.777, 0.793, 0.85, 0.925, 0.995]],
      [-0.05, [0.8, 0.86, 0.925, 0.994]],
    ];
    for (const [height, offsets] of plateRows) {
      for (const offset of offsets) {
        const face = cast([side * offset, height, -0.035], [0, 0, 1]);
        assertClose(face?.point.z, 0);
        assert.equal(
          face.object.material.name,
          'Champagne shoulder wear plate',
        );
      }
    }
    if (levelIndex < 2) {
      for (const centre of [0.81, 0.968]) {
        const head = cast([side * centre, -0.05, -0.02], [0, 0, 1]);
        assertClose(head?.point.z, 0);
        assert.equal(head.object.material.name, 'Brushed fixing steel');

        const seat = cast(
          [side * (centre + 0.00725), -0.050003, -0.02],
          [0, 0, 1],
        );
        assert.equal(seat?.object.material.name, 'Shadow gasket');
        assert.ok(
          seat.point.z > 0.0002 && seat.point.z < 0.00056,
          'actual small countersink',
        );
      }
    }
  }
}

const levels = [];
const evidence = [];
for (let i = 0; i < 3; i++) {
  const level = 'LOD' + i;
  const suffix = i === 0 ? '' : '-lod' + i;
  const path = 'exports/' + slug + suffix + '.glb';
  const bytes = fs.readFileSync(file(path));
  const { issues } = await validator.validateBytes(bytes);
  assert.equal(issues.numErrors, 0);
  assert.equal(issues.numWarnings, 0);

  const buffer = bytes.buffer.slice(
    bytes.byteOffset,
    bytes.byteOffset + bytes.byteLength,
  );
  const { scene, animations, parser } = await new GLTFLoader().parseAsync(
    buffer,
    '',
  );
  scene.updateMatrixWorld(true);
  const root = scene.getObjectByName(
    'ASSET_EscalatorFloorTransition2m_' + level,
  );
  assert.ok(root);
  assert.deepEqual(root.position.toArray(), [0, 0, 0]);
  assert.deepEqual(root.scale.toArray(), [1, 1, 1]);
  assert.equal(animations.length, 0);
  assert.ok(parser.json.buffers.every((buffer) => !buffer.uri));
  assert.equal(parser.json.images?.length ?? 0, 0);

  const bounds = new Box3().setFromObject(root, true);
  for (const [actual, expected] of [
    [bounds.min, [-1, -0.1, 0]],
    [bounds.max, [1, 0, 0.12]],
  ]) {
    actual
      .toArray()
      .forEach((value, axis) => assertClose(value, expected[axis]));
  }
  function cast(origin, direction) {
    const ray = new Raycaster(
      new Vector3(...origin),
      new Vector3(...direction),
      0,
      0.35,
    );
    return ray.intersectObject(root, true)[0];
  }
  const { triangles, draws, ...metrics } = inspectTopology(root);
  const topRays = checkWalkingSurface(cast);
  checkRecess(cast);
  checkShoulders(cast, i);

  levels.push({
    level,
    file: path,
    triangles,
    draws,
    bytes: bytes.length,
    sha256: hash(bytes),
  });
  evidence.push({
    level,
    ...metrics,
    topRays,
    validation: { errors: 0, warnings: 0 },
  });
  if (i > 0) {
    assert.ok(triangles < levels[i - 1].triangles);
    assert.ok(bytes.length < levels[i - 1].bytes);
  }
}
assert.deepEqual(levels, metadata.levels);
for (const key of ['source', 'preview']) {
  assert.equal(
    hash(fs.readFileSync(file(metadata[key]))),
    metadata.sha256[key],
  );
}
assert.equal(levels[0].sha256, metadata.sha256.glb);
console.log(JSON.stringify({ levels, evidence }, null, 2));

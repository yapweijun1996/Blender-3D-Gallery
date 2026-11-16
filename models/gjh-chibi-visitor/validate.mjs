import assert from 'node:assert/strict';
import fs from 'node:fs';
import { validateBytes } from 'gltf-validator';
import { loadCatalog } from '../../scripts/catalog.mjs';

const base = 'models/gjh-chibi-visitor';
const unityVariants = ['terra', 'sol', 'astra'];
const registeredIds = [
  'gjh-chibi-visitor-blender',
  ...unityVariants.map(variant => 'gjh-chibi-visitor-' + variant),
];
const collection = loadCatalog().collections.find(item => item.id === 'gjh-chibi-visitor');
assert.ok(collection, 'GJH Chibi Visitor collection is registered');
assert.deepEqual(collection.assets.map(asset => asset.id), registeredIds, 'Blender wave primary must remain first, followed by the three Unity experiments');

const validatorPackage = JSON.parse(fs.readFileSync('node_modules/gltf-validator/package.json', 'utf8'));
const budgets = {
  default: { triangles: 40000, bytes: 2 * 1024 * 1024 },
  stand: { triangles: 40000, bytes: 2 * 1024 * 1024 },
  kit: { triangles: 175000, bytes: 5 * 1024 * 1024 },
  unity: { triangles: 100000, bytes: 5 * 1024 * 1024 },
};

function readGlb(bytes) {
  assert.equal(bytes.toString('ascii', 0, 4), 'glTF');
  assert.equal(bytes.readUInt32LE(4), 2);
  assert.equal(bytes.readUInt32LE(8), bytes.length);
  const jsonLength = bytes.readUInt32LE(12);
  assert.equal(bytes.readUInt32LE(24 + jsonLength), 0x004e4942, 'GLB contains an embedded BIN chunk');
  return {
    document: JSON.parse(bytes.toString('utf8', 20, 20 + jsonLength)),
    binary: bytes.subarray(28 + jsonLength),
  };
}

function measure(document, bytes) {
  let triangles = 0;
  for (const node of document.nodes ?? []) {
    if (node.mesh === undefined) continue;
    for (const primitive of document.meshes[node.mesh].primitives) {
      assert.equal(primitive.mode ?? 4, 4, 'Only triangle primitives are supported');
      const accessor = document.accessors[primitive.indices ?? primitive.attributes.POSITION];
      assert.equal(accessor.count % 3, 0, 'Triangle accessor count must be divisible by three');
      triangles += accessor.count / 3;
    }
  }
  const positions = new Set(
    (document.meshes ?? []).flatMap(mesh => mesh.primitives.map(primitive => primitive.attributes.POSITION)),
  );
  return {
    glb_bytes: bytes.length,
    triangles,
    vertices: [...positions].reduce((count, index) => count + document.accessors[index].count, 0),
    animations: document.animations?.length ?? 0,
  };
}

const identity = () => [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1];

function multiply(a, b) {
  const result = new Array(16).fill(0);
  for (let column = 0; column < 4; column++) {
    for (let row = 0; row < 4; row++) {
      for (let k = 0; k < 4; k++) result[column * 4 + row] += a[k * 4 + row] * b[column * 4 + k];
    }
  }
  return result;
}

function nodeMatrix(node) {
  if (node.matrix) return node.matrix;
  const [x, y, z, w] = node.rotation ?? [0, 0, 0, 1];
  const [sx, sy, sz] = node.scale ?? [1, 1, 1];
  const [tx, ty, tz] = node.translation ?? [0, 0, 0];
  return [
    (1 - 2 * y * y - 2 * z * z) * sx, (2 * x * y + 2 * w * z) * sx, (2 * x * z - 2 * w * y) * sx, 0,
    (2 * x * y - 2 * w * z) * sy, (1 - 2 * x * x - 2 * z * z) * sy, (2 * y * z + 2 * w * x) * sy, 0,
    (2 * x * z + 2 * w * y) * sz, (2 * y * z - 2 * w * x) * sz, (1 - 2 * x * x - 2 * y * y) * sz, 0,
    tx, ty, tz, 1,
  ];
}

function measureBounds(document, binary, matches = () => true) {
  const min = [Infinity, Infinity, Infinity];
  const max = [-Infinity, -Infinity, -Infinity];
  function visit(index, parent) {
    const node = document.nodes[index];
    const world = multiply(parent, nodeMatrix(node));
    if (node.mesh !== undefined && matches(node)) {
      for (const primitive of document.meshes[node.mesh].primitives) {
        const accessor = document.accessors[primitive.attributes.POSITION];
        const view = document.bufferViews[accessor.bufferView];
        assert.equal(accessor.componentType, 5126, 'Positions use float32 values');
        assert.equal(accessor.type, 'VEC3', 'Positions use VEC3 values');
        const stride = view.byteStride ?? 12;
        const start = (view.byteOffset ?? 0) + (accessor.byteOffset ?? 0);
        for (let i = 0; i < accessor.count; i++) {
          const offset = start + i * stride;
          const x = binary.readFloatLE(offset);
          const y = binary.readFloatLE(offset + 4);
          const z = binary.readFloatLE(offset + 8);
          const point = [
            world[0] * x + world[4] * y + world[8] * z + world[12],
            world[1] * x + world[5] * y + world[9] * z + world[13],
            world[2] * x + world[6] * y + world[10] * z + world[14],
          ];
          point.forEach((value, axis) => {
            min[axis] = Math.min(min[axis], value);
            max[axis] = Math.max(max[axis], value);
          });
        }
      }
    }
    for (const child of node.children ?? []) visit(child, world);
  }
  for (const root of document.scenes[document.scene ?? 0].nodes) visit(root, identity());
  assert.ok(min.every(Number.isFinite) && max.every(Number.isFinite), 'Scene has measurable positions');
  return { min, max, dimensions: max.map((value, axis) => value - min[axis]) };
}

function assertCloseVector(actual, expected, label) {
  assert.equal(actual.length, expected.length, label);
  actual.forEach((value, index) => assert.ok(Math.abs(value - expected[index]) < 1e-6, `${label}[${index}]: ${value} != ${expected[index]}`));
}

async function validateAsset({ id, root, file = id + '.glb', kind = 'unity', registered = true }) {
  const relative = root + '/exports/' + file;
  const bytes = fs.readFileSync(relative);
  const { document, binary } = readGlb(bytes);
  const sceneRoots = document.scenes[document.scene ?? 0].nodes.map(index => document.nodes[index].name);
  assert.deepEqual(sceneRoots, ['GJHChibiVisitor'], id + ' scene root');
  const measured = measure(document, bytes);
  const budget = budgets[kind];
  assert.ok(measured.triangles < budget.triangles, `${id} triangle budget: ${measured.triangles} < ${budget.triangles}`);
  assert.ok(measured.glb_bytes < budget.bytes, `${id} byte budget: ${measured.glb_bytes} < ${budget.bytes}`);
  assert.equal(measured.animations, 0, `${id} remains static with zero clips`);
  assert.equal(document.images?.length ?? 0, 0, `${id} has no embedded images`);
  assert.equal(document.textures?.length ?? 0, 0, `${id} has no textures`);
  assert.ok(document.buffers.every(buffer => buffer.uri === undefined), `${id} is self-contained`);
  const fullBounds = measureBounds(document, binary);
  if (kind === 'default') {
    const metadata = JSON.parse(fs.readFileSync(root + '/metadata.json', 'utf8'));
    assert.deepEqual(metadata.metrics, measured, id + ' measured metadata');
    assertCloseVector(fullBounds.min, metadata.geometry.bounds_glTF_m.min, id + ' bounds min');
    assertCloseVector(fullBounds.max, metadata.geometry.bounds_glTF_m.max, id + ' bounds max');
    assertCloseVector(fullBounds.dimensions, metadata.geometry.bounds_glTF_m.dimensions, id + ' bounds dimensions');
    assert.ok(Math.abs(fullBounds.dimensions[1] - 1) < 1e-6, 'Default model height is one metre within measurement tolerance');
    const hand = measureBounds(document, binary, node => /Body\/L_BlackMitten(?:\.\d+)?(?:__Outline)?(?:\.\d+)?$/.test(node.name ?? ''));
    assert.ok(Math.abs(hand.max[1] - metadata.geometry.raised_left_hand_max_y_metres) < 1e-6, 'Raised hand height matches measured metadata');
    assert.ok(Math.abs(fullBounds.min[1]) < 1e-6, 'Default shoes meet the floor');
    const sceneRoot = document.nodes[document.scenes[document.scene ?? 0].nodes[0]];
    assert.equal(sceneRoot.extras?.pose, 'wave', 'Catalog default GLB uses the R3 static wave pose');
  } else if (kind === 'stand') {
    const sceneRoot = document.nodes[document.scenes[document.scene ?? 0].nodes[0]];
    assert.equal(sceneRoot.extras?.pose, 'stand', 'Alternative export remains neutral standing');
    assert.ok(Math.abs(fullBounds.dimensions[1] - 1) < 1e-6, 'Stand model height is one metre within measurement tolerance');
  }
  if (kind === 'stand' || kind === 'kit') {
    const metadata = JSON.parse(fs.readFileSync(root + '/metadata.json', 'utf8'));
    const measuredExport = {
      ...measured,
      bounds_glTF_m: fullBounds,
      height_metres: fullBounds.dimensions[1],
    };
    assert.deepEqual(metadata.related_exports?.[kind], measuredExport, `${kind} measured metadata`);
    if (kind === 'kit') {
      const sceneRoot = document.nodes[document.scenes[document.scene ?? 0].nodes[0]];
      assert.equal(sceneRoot.extras?.pose, 'stand', 'Kit character remains in its neutral standing pose');
    }
  }
  const result = await validateBytes(new Uint8Array(bytes));
  console.log(`${id}: ${measured.glb_bytes} bytes; ${measured.triangles} triangles; ${measured.vertices} vertices; ${measured.animations} clips; ${result.issues.numErrors} errors; ${result.issues.numWarnings} warnings`);
  if (result.issues.numErrors || result.issues.numWarnings) {
    for (const issue of result.issues.messages.filter(item => item.severity <= 1)) console.error(issue.message);
    throw new Error('Khronos glTF validation failed for ' + id);
  }
  if (registered) {
    const metadataPath = root + '/metadata.json';
    const metadata = JSON.parse(fs.readFileSync(metadataPath, 'utf8'));
    assert.deepEqual(metadata.metrics, measured, id + ' measured metadata');
    metadata.validation = {
      errors: result.issues.numErrors,
      warnings: result.issues.numWarnings,
      validator: validatorPackage.version,
    };
    fs.writeFileSync(metadataPath, JSON.stringify(metadata, null, 2) + '\n');
  }
}

await validateAsset({ id: 'gjh-chibi-visitor-blender', root: base + '/blender', kind: 'default' });
await validateAsset({ id: 'gjh-chibi-visitor-blender-stand', root: base + '/blender', kind: 'stand', registered: false });
await validateAsset({ id: 'gjh-chibi-visitor-blender-kit', root: base + '/blender', file: 'gjh-chibi-visitor-blender-kit.glb', kind: 'kit', registered: false });
for (const variant of unityVariants) {
  await validateAsset({ id: 'gjh-chibi-visitor-' + variant, root: base + '/' + variant, kind: 'unity' });
}

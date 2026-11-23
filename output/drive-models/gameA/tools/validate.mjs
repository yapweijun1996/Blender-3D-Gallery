import assert from 'node:assert/strict';
import { createHash, randomUUID } from 'node:crypto';
import { readFile, writeFile, rename, rm } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import validator from 'gltf-validator';

const root = new URL('../', import.meta.url);
process.chdir(fileURLToPath(root));
const repository = new URL('../../../', root);
const sources = {
  proton_saga: ['models/proton-saga-1985/scene.blend', 'models/proton-saga-1985/exports/proton-saga-1985.glb'],
  hatchback: ['models/hatchback-car/sources/hatchback-car.blend', 'models/hatchback-car/exports/optimized.glb'],
  motorcycle: ['models/motorcycle/sources/motorcycle.blend', 'models/motorcycle/exports/optimized.glb'],
};

async function hashFile(path) {
  return createHash('sha256').update(await readFile(path)).digest('hex');
}

const entries = [
  ['proton_saga', 'car_saga', 5500, 4.1, 'paint glass tire light trim metal chrome plate'],
  ['hatchback', 'car_hatchback_hd', 4500, 4, 'paint glass tire light trim metal plate'],
  ['motorcycle', 'motorbike_hd', 2200, 2, 'paint glass tire light trim metal'],
];
const epsilon = 1e-5;

function readAccessor(document, binary, number) {
  const accessor = document.accessors[number];
  const view = document.bufferViews[accessor.bufferView];
  const fields = accessor.type === 'VEC3' ? 3 : 1;
  const formats = { 5121: ['readUInt8', 1], 5123: ['readUInt16LE', 2], 5125: ['readUInt32LE', 4], 5126: ['readFloatLE', 4] };
  const [read, bytes] = formats[accessor.componentType];
  const start = (view.byteOffset ?? 0) + (accessor.byteOffset ?? 0);
  const stride = view.byteStride ?? fields * bytes;
  return Array.from({ length: accessor.count }, (_, i) => {
    const offset = start + i * stride;
    return fields === 1 ? binary[read](offset) :
      Array.from({ length: fields }, (_, j) => binary[read](offset + j * bytes));
  });
}

function isTriangle(a, b, c) {
  const [ux, uy, uz] = b.map((value, i) => value - a[i]);
  const [vx, vy, vz] = c.map((value, i) => value - a[i]);
  return Math.hypot(uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx) > 1e-11;
}

function inspect(file, bytes, limit, expectedLength, required) {
  assert.equal(bytes.toString('ascii', 0, 4), 'glTF', file);
  assert(bytes.length <= 350_000, `${file} has ${bytes.length}/350000 bytes`);
  const jsonSize = bytes.readUInt32LE(12);
  const doc = JSON.parse(bytes.toString('utf8', 20, 20 + jsonSize));
  const binary = bytes.subarray(28 + jsonSize);
  for (const field of ['images', 'textures', 'skins', 'animations', 'cameras']) {
    assert.equal(doc[field]?.length ?? 0, 0, `${file} contains ${field}`);
  }
  assert(!doc.extensions?.KHR_lights_punctual, file);
  assert.equal(doc.buffers.length, 1, file);
  assert.equal(doc.buffers[0].uri, undefined, file);
  const wheels = expectedLength === 2 ? ['wheel_F', 'wheel_R'] :
    ['wheel_FL', 'wheel_FR', 'wheel_RL', 'wheel_RR'];
  assert.deepEqual(doc.nodes.map(node => node.name).sort(), ['body', ...wheels], file);
  assert.equal(doc.meshes.length, wheels.length + 1, file);
  assert.equal(doc.scenes.length, 1, file);
  assert.equal(doc.scenes[0].nodes.length, wheels.length + 1, file);
  const materials = doc.materials.map(mat => mat.name).sort();
  assert.deepEqual(materials, required.split(' ').sort(), file);
  const lamps = doc.materials.find(mat => mat.name === 'light');
  assert(lamps.emissiveFactor.some(channel => channel > 0), file);
  let triangles = 0;
  let primitiveCount = 0;
  const dims = [[Infinity, Infinity, Infinity], [-Infinity, -Infinity, -Infinity]];
  const wheelPivots = {};
  for (const node of doc.nodes) {
    for (const field of ['rotation', 'scale', 'matrix', 'children']) {
      assert.equal(node[field], undefined, `${file} node ${node.name} has ${field}`);
    }
    const position = node.translation ?? [0, 0, 0];
    const checkWheel = node.name !== 'body';
    if (checkWheel) {
      assert(node.name.startsWith('wheel_F') ? position[2] > 0 : position[2] < 0, node.name);
      if (node.name.endsWith('L')) assert(position[0] < 0, node.name);
      if (node.name.endsWith('R') && wheels.length > 2) assert(position[0] > 0, node.name);
      wheelPivots[node.name] = position.map(value => Number(value.toFixed(6)));
    } else {
      assert.deepEqual(position, [0, 0, 0], file);
    }
    const primitives = doc.meshes[node.mesh].primitives;
    primitiveCount += primitives.length;
    for (const primitive of primitives) {
      assert.equal(primitive.mode ?? 4, 4, file);
      const vertices = readAccessor(doc, binary, primitive.attributes.POSITION);
      const normals = readAccessor(doc, binary, primitive.attributes.NORMAL);
      const indices = readAccessor(doc, binary, primitive.indices);
      assert.equal(vertices.length, normals.length, file);
      assert(!Object.keys(primitive.attributes).some(key => key.startsWith('TEXCOORD')), file);
      for (const normal of normals) assert(Math.abs(Math.hypot(...normal) - 1) < .0001, file);
      for (let i = 0; i < indices.length; i += 3) {
        const tri = indices.slice(i, i + 3).map(index => vertices[index]);
        assert(isTriangle(...tri), `${file} contains a degenerate triangle at ${JSON.stringify(tri)}`);
      }
      triangles += indices.length / 3;
      if (checkWheel && doc.materials[primitive.material].name === 'tire') {
        const limits = [0, 1, 2].map(axis => {
          const values = vertices.map(vertex => vertex[axis]);
          return [Math.min(...values), Math.max(...values)];
        });
        for (const [lo, hi] of limits.slice(1)) {
          assert(Math.abs(hi + lo) < epsilon, `${file} off-centre wheel ${node.name}`);
        }
        assert(Math.abs(limits[1][1] - limits[2][1]) < epsilon, `${file} invalid wheel axle ${node.name}`);
        assert(limits[0][1] - limits[0][0] < limits[1][1] - limits[1][0], `${file} invalid wheel thickness ${node.name}`);
      }
      for (const vertex of vertices) {
        for (let axis = 0; axis < 3; axis++) {
          dims[0][axis] = Math.min(dims[0][axis], vertex[axis] + position[axis]);
          dims[1][axis] = Math.max(dims[1][axis], vertex[axis] + position[axis]);
        }
      }
    }
  }
  assert(primitiveCount > 0 && primitiveCount <= 16, `${file} has ${primitiveCount} primitives`);
  assert(triangles > 0 && triangles <= limit, `${file} has ${triangles}/${limit} triangles`);
  assert(Math.abs(dims[0][1]) < epsilon, `${file} does not sit on y=0`);
  for (const axis of [0, 2]) assert(Math.abs(dims[0][axis] + dims[1][axis]) < epsilon, file);
  const size = dims[1].map((max, axis) => max - dims[0][axis]);
  assert(Math.abs(size[2] - expectedLength) < epsilon, `${file} length ${size[2]}`);
  return {
    file, triangles, bytes: bytes.length, size_m: size.map(value => Number(value.toFixed(4))),
    primitives: primitiveCount, materials, wheel_pivots_m: wheelPivots,
  };
}

const results = [];
for (const [model, name, limit, length, materials] of entries) {
  const file = `${name}.glb`;
  const bytes = await readFile(file);
  const validation = await validator.validateBytes(new Uint8Array(bytes), { uri: file, maxIssues: 0 });
  const { numErrors: errors, numWarnings: warnings, numInfos: infos, numHints: hints, messages } = validation.issues;
  console.log(file, { errors, warnings, infos, hints }, messages);
  assert.equal(errors + warnings, 0, file);
  const info = inspect(file, bytes, limit, length, materials);
  const [scene, original] = sources[model];
  const sheet = `contact-sheets/${name}.png`;
  const [sceneHash, originalHash, sheetHash] = await Promise.all([
    hashFile(new URL(scene, repository)),
    hashFile(new URL(original, repository)),
    hashFile(sheet),
  ]);
  results.push({
    model, ...info,
    sha256: createHash('sha256').update(bytes).digest('hex'),
    validator: { version: validation.validatorVersion, errors, warnings, infos, hints },
    source: { scene, scene_sha256: sceneHash, original_glb: original, original_sha256: originalHash },
    six_view_comparison: {
      file: sheet,
      sha256: sheetHash,
      renderer: 'Blender 5.1.2 Cycles CPU',
      threads: 2,
      samples: 12,
      views: ['front', 'left', 'rear', 'right', 'front-quarter', 'rear-quarter'],
      order_within_pair: ['original', 'game'],
    },
  });
}
const pending = `.models-${randomUUID()}.json`;
try {
  await writeFile(pending, JSON.stringify(results, null, 2) + '\n', { flag: 'wx', flush: true });
  await rename(pending, 'models.json');
} finally {
  await rm(pending, { force: true });
}
console.table(results.map(({ file, triangles, bytes, size_m, primitives }) => ({ file, triangles, bytes, size_m, primitives })));

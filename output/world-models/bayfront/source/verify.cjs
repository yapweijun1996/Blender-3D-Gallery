const assert = require('node:assert/strict');
const fs = require('node:fs/promises');
const path = require('node:path');
const validator = require('../../../../node_modules/gltf-validator');

const folder = path.resolve(__dirname, '..');
const allowed = new Set('paint glass window wall roof concrete metal chrome trim stone water leaf trunk light lamp_emissive rubber plate'.split(' '));
const targets = [
  ['bayfront_concourse.glb', 50, 25, 9000],
  ['bayfront_platform_circle.glb', 140, 11, 8000],
  ['bayfront_platform_downtown.glb', 140, 11, 8000],
  ['bayfront_entrance.glb', 14, 8, 3500],
];
const rounded = (value) => Number(value.toFixed(4));

function jpegSize(data) {
  assert.equal(data.readUInt16BE(0), 0xffd8, 'JPEG header');
  for (let p = 2; p < data.length;) {
    const marker = data[p + 1];
    const length = data.readUInt16BE(p + 2);
    if ([0xc0, 0xc1, 0xc2].includes(marker)) {
      return [data.readUInt16BE(p + 7), data.readUInt16BE(p + 5)];
    }
    assert(length >= 2);
    p += length + 2;
  }
  throw new Error('JPEG dimensions unavailable');
}

async function inspect([file, length, depth, budget]) {
  const bytes = await fs.readFile(path.join(folder, file));
  const report = await validator.validateBytes(new Uint8Array(bytes), {uri: file});
  if (report.issues.numErrors || report.issues.numWarnings) {
    console.error(file, report.issues);
    throw new Error('glTF Validator reported errors or warnings');
  }
  assert.equal(bytes.toString('ascii', 0, 4), 'glTF');
  assert.equal(bytes.readUInt32LE(4), 2);
  assert.equal(bytes.length, bytes.readUInt32LE(8));
  assert(bytes.length <= 1.8 * 1024 * 1024);
  const jsonLength = bytes.readUInt32LE(12);
  const gltf = JSON.parse(bytes.toString('utf8', 20, 20 + jsonLength));
  const binaryStart = 28 + jsonLength;
  assert.match(gltf.asset.generator, /Blender.*5\.1\.2/i);
  assert.equal(gltf.buffers.length, 1);
  assert(!gltf.buffers.some((buffer) => buffer.uri));
  for (const key of ['animations', 'skins', 'cameras', 'extensionsRequired']) {
    assert.equal(gltf[key]?.length ?? 0, 0, key);
  }
  assert(!gltf.extensionsUsed?.includes('KHR_lights_punctual'));
  assert((gltf.images?.length ?? 0) <= 1 && (gltf.textures?.length ?? 0) <= 1);
  for (const img of gltf.images ?? []) {
    assert(!img.uri);
    assert.equal(img.mimeType, 'image/jpeg');
    const view = gltf.bufferViews[img.bufferView];
    const offset = binaryStart + (view.byteOffset ?? 0);
    assert.deepEqual(jpegSize(bytes.subarray(offset, offset + view.byteLength)), [1024, 1024]);
  }
  const materials = gltf.materials.map((m) => m.name).sort();
  assert.equal(new Set(materials).size, materials.length);
  assert(materials.every((m) => allowed.has(m)));
  assert(gltf.materials.every((m) => m.name === 'plate' || !m.pbrMetallicRoughness.baseColorTexture));

  const lower = [Infinity, Infinity, Infinity];
  const upper = [-Infinity, -Infinity, -Infinity];
  const sceneRoots = gltf.scenes[gltf.scene ?? 0].nodes;
  const deckName = {
    'bayfront_concourse.glb': 'Concourse_Terrazzo_Deck',
    'bayfront_entrance.glb': 'Exit_B_Tiled_Street_Apron'
  }[file] ?? 'Island_Tiled_Platform_Deck';
  let verifiedDatum = false;
  let verifiedFront = false;
  assert.equal(sceneRoots.length, gltf.meshes.length);
  let triangles = 0;
  const parts = [];
  for (const index of sceneRoots) {
    const node = gltf.nodes[index];
    assert(!node.children && !node.rotation && !node.scale && !node.matrix && !node.translation);
    assert(!parts.includes(node.name));
    parts.push(node.name);
    for (const primitive of gltf.meshes[node.mesh].primitives) {
      assert.equal(primitive.mode ?? 4, 4);
      const positions = gltf.accessors[primitive.attributes.POSITION];
      const material = gltf.materials[primitive.material].name;
      if (node.name === deckName && material === 'stone') {
        assert.equal(rounded(positions.min[1]), 0);
        assert.equal(rounded(positions.max[1]), 0);
        verifiedDatum = true;
      }
      if (material === 'plate' && positions.max[2] > 0) {
        verifiedFront = true;
      }
      triangles += (primitive.indices === undefined ? positions.count : gltf.accessors[primitive.indices].count) / 3;
      for (let axis = 0; axis < 3; axis++) {
        lower[axis] = Math.min(lower[axis], positions.min[axis]);
        upper[axis] = Math.max(upper[axis], positions.max[axis]);
      }
    }
  }
  assert(verifiedDatum && verifiedFront, 'floor datum or front wayfinding missing');
  const bounds = {min: lower.map(rounded), max: upper.map(rounded)};
  const size = upper.map((edge, axis) => rounded(edge - lower[axis]));
  assert.deepEqual([size[0], size[2]], [length, depth], file);
  assert.deepEqual([bounds.min[0], bounds.max[0], bounds.min[2], bounds.max[2]], [-length/2, length/2, -depth/2, depth/2]);
  assert(lower[1] < 0 && upper[1] > 0, 'floor datum crosses structural bounds');
  console.log(file, triangles, 'triangles', bytes.length, 'bytes', size.join(' × '), 'm', parts.length, 'parts');
  assert(Number.isInteger(triangles) && triangles <= budget, file + ' triangle budget');
  return {
    file, triangles, bytes: bytes.length, size_metres: {x: size[0], y: size[1], z: size[2]},
    bounds_metres: bounds, materials, parts,
    validator: {version: report.validatorVersion, errors: report.issues.numErrors, warnings: report.issues.numWarnings}
  };
}

(async () => {
  const models = [];
  for (const spec of targets) models.push(await inspect(spec));
  await fs.writeFile(path.join(folder, 'models.json'), JSON.stringify(models, null, 2) + '\n');
})().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});

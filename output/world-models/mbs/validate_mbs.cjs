/* Validate the exported geometry and emit the game handoff manifest. */
const assert = require('node:assert/strict');
const { createHash } = require('node:crypto');
const { readFileSync, writeFileSync } = require('node:fs');
const { join } = require('node:path');
const validator = require('../../../node_modules/gltf-validator');

const materialNames = new Set([
  'paint', 'glass', 'window', 'wall', 'roof', 'concrete', 'metal', 'chrome',
  'trim', 'stone', 'water', 'leaf', 'trunk', 'light', 'lamp_emissive', 'rubber', 'plate',
]);

function position(buffer, asset, primitive, visit) {
  const accessor = asset.accessors[primitive.attributes.POSITION];
  const view = asset.bufferViews[accessor.bufferView];
  assert.equal(accessor.componentType, 5126);
  const offset = (view.byteOffset ?? 0) + (accessor.byteOffset ?? 0);
  for (let i = 0; i < accessor.count; i++) {
    const start = offset + i * (view.byteStride ?? 12);
    visit([buffer.readFloatLE(start), buffer.readFloatLE(start + 4), buffer.readFloatLE(start + 8)]);
  }
}

function inspect(data) {
  assert.equal(data.toString('ascii', 0, 4), 'glTF');
  assert.equal(data.readUInt32LE(4), 2);
  assert.equal(data.readUInt32LE(8), data.length);
  const end = 20 + data.readUInt32LE(12);
  const asset = JSON.parse(data.toString('utf8', 20, end));
  const buffer = data.subarray(end + 8);
  for (const key of ['animations', 'skins', 'cameras']) {
    assert.equal(asset[key]?.length ?? 0, 0, key);
  }
  assert(!asset.extensionsUsed?.includes('KHR_lights_punctual'));
  assert.equal(asset.buffers.length, 1);
  assert.equal(asset.buffers[0].uri, undefined);
  const images = asset.images ?? [];
  assert(images.length <= 1);
  for (const image of images) {
    assert.equal(image.mimeType, 'image/jpeg');
    assert.equal(image.uri, undefined);
    const view = asset.bufferViews[image.bufferView];
    const jpeg = buffer.subarray(view.byteOffset ?? 0, (view.byteOffset ?? 0) + view.byteLength);
    assert.equal(jpeg.readUInt16BE(0), 0xffd8);
    let offset = 2;
    let dimensions;
    while (offset < jpeg.length) {
      const marker = jpeg.readUInt16BE(offset);
      if (marker === 0xffc0 || marker === 0xffc2) {
        dimensions = [jpeg.readUInt16BE(offset + 5), jpeg.readUInt16BE(offset + 7)];
        break;
      }
      offset += 2 + jpeg.readUInt16BE(offset + 2);
    }
    assert.deepEqual(dimensions, [1024, 1024]);
  }

  const min = [Infinity, Infinity, Infinity];
  const max = [-Infinity, -Infinity, -Infinity];
  const ground = { minX: Infinity, maxX: -Infinity, minZ: Infinity, maxZ: -Infinity };
  const parts = asset.nodes.map(node => {
    for (const key of ['translation', 'rotation', 'scale', 'matrix', 'children']) {
      assert.equal(node[key], undefined, node.name + ' ' + key);
    }
    assert(Number.isInteger(node.mesh), 'Each node must be a mesh part');
    let triangles = 0;
    for (const primitive of asset.meshes[node.mesh].primitives) {
      assert.equal(primitive.mode ?? 4, 4);
      const count = asset.accessors[primitive.indices].count;
      assert.equal(count % 3, 0);
      triangles += count / 3;
      position(buffer, asset, primitive, point => {
        for (let axis = 0; axis < 3; axis++) {
          min[axis] = Math.min(min[axis], point[axis]);
          max[axis] = Math.max(max[axis], point[axis]);
        }
        const [x, y, z] = point;
        if (Math.abs(y) < .0001) {
          ground.minX = Math.min(ground.minX, x);
          ground.maxX = Math.max(ground.maxX, x);
          ground.minZ = Math.min(ground.minZ, z);
          ground.maxZ = Math.max(ground.maxZ, z);
        }
      });
    }
    return { name: node.name, triangles };
  });
  assert(Math.abs(min[1]) < .0001, 'Lowest vertex must sit at Y=0');
  assert(Math.abs(ground.minX + ground.maxX) < .001, 'Ground center X');
  assert(Math.abs(ground.minZ + ground.maxZ) < .001, 'Ground center Z');
  assert.equal(new Set(parts.map(part => part.name)).size, parts.length);
  const materials = asset.materials.map(material => material.name).sort();
  assert(materials.every(name => materialNames.has(name)), materials.join(', '));
  const [x,y,z] = max.map((value, axis) => Math.round((value - min[axis]) * 1000) / 1000);
  return { triangles: parts.reduce((count, part) => count + part.triangles, 0),
    size_metres: { x, y, z }, materials, parts, facade_atlases: images.length };
}

async function main() {
  const models = [];
  for (const [file, budget] of [['mbs_towers.glb', 14000], ['mbs_podium.glb', 11000]]) {
    const data = readFileSync(join(__dirname, file));
    const report = await validator.validateBytes(new Uint8Array(data), { uri: file });
    const { numErrors: errors, numWarnings: warnings } = report.issues;
    const sha256 = createHash('sha256').update(data).digest('hex');
    const model = { file, bytes: data.length, sha256, ...inspect(data),
      validator: { version: report.validatorVersion, errors, warnings } };
    console.log(file, model.triangles, model.bytes, model.size_metres, model.validator);
    if (errors || warnings) console.log(report.issues.messages.filter(issue => issue.severity < 2));
    models.push(model);
    assert(data.length <= Math.floor(1.8 * 1024 ** 2), file + ' exceeds the byte budget');
    assert(model.triangles <= budget, file + ' exceeds the triangle budget');
    assert.equal(errors, 0, file + ' validation errors');
    assert.equal(warnings, 0, file + ' validation warnings');
  }
  writeFileSync(join(__dirname, 'models.json'), JSON.stringify(models, null, 2) + '\n');
}

main().catch(error => {
  console.error(error);
  process.exitCode = 1;
});

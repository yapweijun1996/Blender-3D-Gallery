const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const validator = require('../../../node_modules/gltf-validator');

const allowed = new Set([
  'paint', 'glass', 'window', 'wall', 'roof', 'concrete', 'metal', 'chrome', 'trim',
  'stone', 'water', 'leaf', 'trunk', 'light', 'lamp_emissive', 'rubber', 'plate',
]);

function measure(buffer, gltf) {
  const minimum = [Infinity, Infinity, Infinity];
  const maximum = [-Infinity, -Infinity, -Infinity];
  const offsets = [0, 1, 2].map((axis) => axis * 4);
  const binHeader = 20 + buffer.readUInt32LE(12);
  assert.equal(buffer.readUInt32LE(binHeader + 4), 0x004e4942);
  const bin = binHeader + 8;
  const parts = gltf.nodes.map((node) => {
    for (const field of ['camera', 'skin', 'matrix', 'rotation', 'translation', 'scale', 'children']) {
      assert.equal(node[field], undefined, `Unexpected ${field} on ${node.name}`);
    }
    const mesh = gltf.meshes[node.mesh];
    assert.equal(mesh.name, node.name);
    let triangles = 0;
    for (const primitive of mesh.primitives) {
      assert.equal(primitive.mode ?? 4, 4);
      const positions = gltf.accessors[primitive.attributes.POSITION];
      const view = gltf.bufferViews[positions.bufferView];
      const indices = gltf.accessors[primitive.indices];
      const indexView = gltf.bufferViews[indices.bufferView];
      const indexByteWidth = indices.componentType === 5123 ? 2 : 4;
      assert.ok([5123, 5125].includes(indices.componentType));
      assert.equal(indices.count % 3, 0);
      assert.equal(positions.componentType, 5126);
      const positionStart = bin + (view.byteOffset ?? 0) + (positions.byteOffset ?? 0);
      const indexStart = bin + (indexView.byteOffset ?? 0) + (indices.byteOffset ?? 0);
      const points = Array.from({ length: positions.count }, (_, index) => {
        const start = positionStart + index * (view.byteStride ?? 12);
        const point = offsets.map((offset) => buffer.readFloatLE(start + offset));
        point.forEach((coordinate, axis) => {
          minimum[axis] = Math.min(minimum[axis], coordinate);
          maximum[axis] = Math.max(maximum[axis], coordinate);
        });
        return point;
      });
      for (let index = 0; index < indices.count; index += 3) {
        const triangle = [0, 1, 2].map((vertex) => {
          const start = indexStart + (index + vertex) * indexByteWidth;
          const pointIndex = indexByteWidth === 2 ? buffer.readUInt16LE(start) : buffer.readUInt32LE(start);
          return points[pointIndex];
        });
        const [a, b, c] = triangle;
        const ab = b.map((coordinate, axis) => coordinate - a[axis]);
        const ac = c.map((coordinate, axis) => coordinate - a[axis]);
        const twiceArea = Math.hypot(ab[1]*ac[2]-ab[2]*ac[1], ab[2]*ac[0]-ab[0]*ac[2], ab[0]*ac[1]-ab[1]*ac[0]);
        assert.ok(twiceArea > 1e-8, `Degenerate triangle in ${node.name} at ${index / 3}`);
      }
      triangles += indices.count / 3;
    }
    return { name: node.name, triangles };
  });
  return { parts, minimum, maximum };
}

async function inspect(file, triangleBudget) {
  const buffer = fs.readFileSync(path.join(__dirname, file));
  assert.ok(buffer.length <= 1.8 * 1024 * 1024);
  assert.equal(buffer.toString('ascii', 0, 4), 'glTF');
  const gltf = JSON.parse(buffer.toString('utf8', 20, 20 + buffer.readUInt32LE(12)));
  assert.equal(gltf.buffers.length, 1);
  assert.ok(gltf.buffers.every((entry) => entry.uri === undefined));
  for (const field of ['animations', 'cameras', 'skins', 'images', 'textures', 'extensionsUsed']) {
    assert.equal(gltf[field], undefined);
  }
  const materials = gltf.materials.map((material) => material.name).sort();
  assert.ok(materials.every((name) => allowed.has(name)));
  assert.equal(new Set(materials).size, materials.length);
  const result = await validator.validateBytes(new Uint8Array(buffer), { uri: file });
  assert.equal(result.issues.numErrors, 0, JSON.stringify(result.issues.messages));
  assert.equal(result.issues.numWarnings, 0, JSON.stringify(result.issues.messages));

  const { parts, minimum, maximum } = measure(buffer, gltf);
  const triangles = parts.reduce((sum, part) => sum + part.triangles, 0);
  assert.ok(triangles <= triangleBudget, `${file} has ${triangles} triangles`);
  if (file.endsWith('_base.glb')) {
    assert.equal(minimum[1], 0);
    assert.ok(Math.abs(minimum[0] + maximum[0]) < .01);
    assert.ok(Math.abs(minimum[2] + maximum[2]) < .01);
  } else {
    assert.ok(minimum[1] > 5 && maximum[1] < 45);
  }

  return {
    file,
    triangles,
    bytes: buffer.length,
    size_m: Object.fromEntries(['x', 'y', 'z'].map((axis, i) => [axis, +((maximum[i]-minimum[i]).toFixed(3))])),
    materials,
    parts,
    validator: {
      version: result.validatorVersion,
      errors: result.issues.numErrors,
      warnings: result.issues.numWarnings,
      infos: result.issues.numInfos,
      hints: result.issues.numHints,
    },
  };
}

async function main() {
  const models = await Promise.all([
    inspect('esplanade_domes.glb', 18000),
    inspect('esplanade_base.glb', 9000),
  ]);
  const manifest = {
    blender: '5.1.2',
    units: 'metres',
    up: '+Y',
    front: '+Z',
    origin: 'Shared site centre on ground. Load both files at the same transform.',
    models,
  };
  fs.writeFileSync(path.join(__dirname, 'models.json'), JSON.stringify(manifest, null, 2) + '\n');
  for (const { file, triangles, bytes, size_m, validator } of models) {
    console.log(JSON.stringify({ file, triangles, bytes, size_m, validator }));
  }
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});

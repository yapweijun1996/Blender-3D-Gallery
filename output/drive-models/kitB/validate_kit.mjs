import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { readFile, writeFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import validator from 'gltf-validator';

const directory = new URL('./', import.meta.url);
const specs = {
  tree_raintree: [900, [16, 14, null]],
  tree_palm: [600, [null, 12, null]],
  tree_street: [400, [5, 8, 5]],
  shrub_hedge: [120, [.8, 1, 4]],
  building_hdb: [1800, [70, 38, 14]],
  building_tower_glass: [900, [30, 120, 30]],
  building_shophouse: [1800, [22, 12, 8]],
  building_condo: [1600, [40, 55, 25]],
  building_lowrise: [900, [30, 15, 12]],
  landmark_mbs: [3500, []],
  landmark_checkpoint: [2800, [40]],
  landmark_southkey: [3000, [null, 150]],
};
const allowed = new Set([
  'paint', 'glass', 'tire', 'light', 'trim', 'wall', 'roof',
  'window', 'leaf', 'trunk', 'metal', 'concrete',
]);
const required = {
  tree_raintree: ['trunk', 'leaf'],
  building_hdb: ['wall', 'window', 'roof', 'concrete', 'trim'],
  building_tower_glass: ['window', 'metal', 'concrete'],
  landmark_mbs: ['wall', 'window', 'metal', 'concrete'],
};
const validatorVersion = validator.version();
const models = [];
const validation = { validator: 'Khronos glTF Validator', version: validatorVersion, models: {} };
const round = number => Number(number.toFixed(4));
let failed = false;

for (const [name, [budget, target]] of Object.entries(specs)) {
  const file = name + '.glb';
  const bytes = await readFile(new URL(file, directory));
  const report = await validator.validateBytes(new Uint8Array(bytes), { uri: file, maxIssues: 100 });
  validation.models[name] = {
    sha256: createHash('sha256').update(bytes).digest('hex'),
    ...report.issues,
  };
  try {
    assert.equal(report.issues.numErrors, 0, 'validator errors');
    assert.equal(report.issues.numWarnings, 0, 'validator warnings');
    assert.equal(bytes.toString('ascii', 0, 4), 'glTF');
    const jsonLength = bytes.readUInt32LE(12);
    const gltf = JSON.parse(bytes.toString('utf8', 20, 20 + jsonLength));
    const dataOffset = 28 + jsonLength;
    assert.equal(gltf.buffers.length, 1);
    assert.equal(gltf.buffers[0].uri, undefined);
    for (const key of ['animations', 'skins', 'cameras', 'images', 'textures', 'extensionsUsed']) {
      assert.equal(gltf[key]?.length ?? 0, 0, key);
    }
    const roots = gltf.scenes[gltf.scene].nodes;
    assert.equal(roots.length, gltf.nodes.length);
    assert.equal(roots.length, name === 'landmark_checkpoint' ? 5 : 1);

    const materialNames = gltf.materials.map(material => {
      assert(allowed.has(material.name));
      assert(material.pbrMetallicRoughness);
      assert(!material.emissiveFactor && !material.alphaMode);
      return material.name;
    }).sort();
    assert.equal(new Set(materialNames).size, materialNames.length);
    for (const key of required[name] ?? []) assert(materialNames.includes(key));

    let triangles = 0;
    let primitives = 0;
    const minimum = [Infinity, Infinity, Infinity];
    const maximum = [-Infinity, -Infinity, -Infinity];
    const barriers = {};
    const hedgeEnds = [new Set(), new Set()];
    for (const nodeId of roots) {
      const node = gltf.nodes[nodeId];
      assert(node.mesh !== undefined && !node.children && !node.matrix);
      assert(!node.rotation && !node.scale, 'rotation/scale must be baked');
      const translation = node.translation ?? [0, 0, 0];
      const pivotMin = [Infinity, Infinity, Infinity];
      const pivotMax = [-Infinity, -Infinity, -Infinity];

      for (const primitive of gltf.meshes[node.mesh].primitives) {
        assert.equal(primitive.mode ?? 4, 4);
        assert(primitive.indices !== undefined && primitive.material !== undefined);
        assert.deepEqual(Object.keys(primitive.attributes).sort(), ['NORMAL', 'POSITION']);
        const position = gltf.accessors[primitive.attributes.POSITION];
        const indices = gltf.accessors[primitive.indices];
        const view = gltf.bufferViews[position.bufferView];
        assert.equal(position.componentType, 5126);
        assert.equal(position.type, 'VEC3');
        assert.equal(indices.count % 3, 0);
        triangles += indices.count / 3;
        primitives++;
        for (let vertex = 0; vertex < position.count; vertex++) {
          const offset = dataOffset + (view.byteOffset ?? 0) + (position.byteOffset ?? 0)
            + vertex * (view.byteStride ?? 12);
          const local = Array.from({ length: 3 }, (_, axis) => bytes.readFloatLE(offset + axis * 4));
          for (let axis = 0; axis < 3; axis++) {
            const world = local[axis] + translation[axis];
            minimum[axis] = Math.min(minimum[axis], world);
            maximum[axis] = Math.max(maximum[axis], world);
            pivotMin[axis] = Math.min(pivotMin[axis], local[axis]);
            pivotMax[axis] = Math.max(pivotMax[axis], local[axis]);
          }
          if (name === 'shrub_hedge' && Math.abs(Math.abs(local[2]) - 2) < 1e-6) {
            hedgeEnds[local[2] < 0 ? 0 : 1].add(local.slice(0, 2).map(round).join(','));
          }
        }
      }
      if (node.name === name) {
        assert.deepEqual(translation, [0, 0, 0]);
      } else {
        assert.equal(name, 'landmark_checkpoint');
        assert.match(node.name, /^barrier_[1-4]$/);
        assert(pivotMin[0] < 0 && pivotMin[0] > -.16 && pivotMax[0] > 6.75);
        assert(pivotMin[1] < 0 && pivotMax[1] > 0 && pivotMax[1] < .13);
        assert(pivotMin[2] < 0 && pivotMax[2] > 0 && pivotMax[2] < .13);
        const index = Number(node.name.slice(-1));
        const expectedPivot = [-16.8 + (index - 1) * 8.4 + .63, 1.08, 2.83];
        assert(translation.every((coordinate, axis) => Math.abs(coordinate - expectedPivot[axis]) < 1e-5));
        // An arm along local +X rises along +Y under a positive local Z rotation.
        barriers[node.name] = { pivot_m: translation.map(round), lift_axis: 'Z' };
      }
    }
    if (name === 'landmark_checkpoint') {
      assert.deepEqual(Object.keys(barriers).sort(), [1, 2, 3, 4].map(i => 'barrier_' + i));
      validation.models[name].barriers = barriers;
    }
    if (name === 'shrub_hedge') {
      assert(hedgeEnds[0].size >= 10, 'expected clipped end profiles');
      assert.deepEqual(hedgeEnds[0], hedgeEnds[1]);
    }
    assert(Math.abs(minimum[1]) < .0001, `ground is y=${minimum[1]}`);
    const size = maximum.map((value, axis) => value - minimum[axis]);
    target.forEach((meters, axis) => {
      if (meters != null) assert(Math.abs(size[axis] - meters) < .025, `axis ${axis}: ${size[axis]} m`);
    });
    assert(triangles <= budget, `${triangles}/${budget} triangles`);
    assert(primitives <= 16, `${primitives}/16 primitives`);
    const model = {
      file, triangles, bytes: bytes.length,
      bounding_box_size_m: size.map(round),
      material_names: materialNames,
    };
    models.push(model);
    Object.assign(validation.models[name], { primitives, triangles, budget });
    console.log(name, triangles, bytes.length, size.map(round).join(' × '), primitives, '0/0');
  } catch (error) {
    validation.models[name].failed_check = error.message;
    console.error(name, error.message, report.issues.messages);
    failed = true;
  }
}
await writeFile(fileURLToPath(new URL('validation.json', directory)),
  JSON.stringify(validation, null, 2) + '\n');
if (failed) {
  process.exitCode = 1;
} else {
  await writeFile(fileURLToPath(new URL('models.json', directory)),
    JSON.stringify({ axis_order: ['X', 'Y', 'Z'], models }, null, 2) + '\n');
}

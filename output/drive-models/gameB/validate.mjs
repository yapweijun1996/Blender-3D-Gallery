import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { readFile, rename, writeFile } from 'node:fs/promises';
import validator from 'gltf-validator';

const folder = new URL('./', import.meta.url);
const specs = [
  { model: 'singapore-public-bus', file: 'bus_hd.glb', length: 12, budget: 6500, front: 5.95 },
  { model: 'delivery-van', file: 'van_hd.glb', length: 4.9, budget: 4500, front: 2.2 },
  { model: 'cargo-truck', file: 'truck_hd.glb', length: 8.8, budget: 5000, front: 4.2 },
];
const approvedSlots = new Set(['paint','glass','tire','light','trim','metal','chrome','plate']);
const wheels = ['wheel_FL','wheel_FR','wheel_RL','wheel_RR'];
const tol = 0.0001;
const rounded = number => Number(number.toFixed(5));

function bounds() {
  return { min: [Infinity,Infinity,Infinity], max: [-Infinity,-Infinity,-Infinity] };
}

function extend(target, min, max) {
  for (let axis = 0; axis < 3; axis++) {
    target.min[axis] = Math.min(target.min[axis], min[axis]);
    target.max[axis] = Math.max(target.max[axis], max[axis]);
  }
}

async function validate(spec) {
  const bytes = await readFile(new URL(spec.file, folder));
  const result = await validator.validateBytes(new Uint8Array(bytes), { uri: spec.file, maxIssues: 100 });
  if (result.issues.numErrors || result.issues.numWarnings) console.error(spec.file, result.issues);
  assert.equal(result.issues.numErrors, 0);
  assert.equal(result.issues.numWarnings, 0);
  assert(bytes.length <= 350_000, spec.file);
  assert.equal(bytes.toString('ascii',0,4), 'glTF');
  const gltf = JSON.parse(bytes.toString('utf8',20,20+bytes.readUInt32LE(12)));
  const materialNames = gltf.materials.map(m => m.name);
  assert.equal(new Set(materialNames).size, materialNames.length);
  assert(materialNames.every(m => approvedSlots.has(m)));
  for (const name of ['paint','glass','tire','light','trim','metal','chrome']) {
    assert(materialNames.includes(name), name);
  }
  assert(gltf.materials.find(m => m.name === 'light').emissiveFactor?.some(v => v > 0));
  assert(gltf.materials.find(m => m.name === 'paint').pbrMetallicRoughness.baseColorFactor);
  assert.equal(gltf.buffers.length, 1);
  assert.equal(gltf.buffers[0].uri, undefined);
  for (const key of ['animations','skins','cameras','textures','images','extensionsUsed']) {
    assert.equal(gltf[key]?.length ?? 0, 0, key);
  }
  assert.equal(gltf.scenes.length, 1);
  assert.deepEqual(gltf.scenes[0].nodes, [0,1,2,3,4]);
  assert.deepEqual(gltf.nodes.map(n => n.name), ['body', ...wheels]);
  assert.equal(gltf.meshes.length, 5);
  assert.deepEqual(gltf.nodes[0].translation, [0,0,0]);

  let triangles = 0;
  let primitives = 0;
  const modelBounds = bounds();
  const wheelPivots = {};
  for (const node of gltf.nodes) {
    assert(!node.rotation && !node.scale && !node.matrix && !node.children);
    const pivot = node.translation;
    const mesh = gltf.meshes[node.mesh];
    assert.equal(mesh.name, node.name);
    const nodeSlots = new Set();
    for (const prim of mesh.primitives) {
      assert.equal(prim.mode ?? 4, 4);
      const name = materialNames[prim.material];
      assert(!nodeSlots.has(name), `Multiply drawn material ${node.name}/${name}`);
      nodeSlots.add(name);
      const { POSITION, NORMAL, COLOR_0 } = prim.attributes;
      assert(POSITION !== undefined && NORMAL !== undefined);
      assert.equal(Object.keys(prim.attributes).length, COLOR_0 === undefined ? 2 : 3);
      const { min, max } = gltf.accessors[POSITION];
      const count = gltf.accessors[prim.indices].count;
      assert.equal(count % 3, 0);
      triangles += count/3;
      primitives++;
      extend(modelBounds, min.map((n,i) => n+pivot[i]), max.map((n,i) => n+pivot[i]));
      if (name === 'tire') {
        assert(node.name.startsWith('wheel_'));
        assert(pivot[1] > 0 && Math.abs(min[1]+pivot[1]) < tol, node.name);
        for (let i = 0; i < 3; i++) assert(Math.abs(min[i]+max[i]) < tol, node.name);
        assert(max[0] < max[1] && Math.abs(max[1]-max[2]) < tol, node.name);
      }
      if (name === 'light') assert(max[2] > spec.front, 'Headlamps must face +Z');
    }
    if (node.name.startsWith('wheel_')) {
      assert.deepEqual([...nodeSlots].sort(), ['metal', 'tire']);
      assert.equal(Math.sign(pivot[0]), node.name.endsWith('L') ? -1 : 1);
      assert.equal(Math.sign(pivot[2]), node.name.startsWith('wheel_F') ? 1 : -1);
      wheelPivots[node.name] = pivot.map(rounded);
    }
  }

  const { min, max } = modelBounds;
  const [width, height, length] = max.map((value, axis) => value-min[axis]);
  assert(Math.abs(min[0]+max[0]) < tol && Math.abs(min[2]+max[2]) < tol);
  assert(Math.abs(min[1]) < tol);
  assert(Math.abs(length-spec.length) < tol);
  assert(triangles <= spec.budget);
  assert(primitives <= 16);
  console.log(spec.file, triangles, 'triangles', primitives, 'primitives', bytes.length, 'bytes', '0 errors / 0 warnings');

  return {
    model: spec.model, file: spec.file, triangles, bytes: bytes.length, primitives,
    size_m: { length: rounded(length), width: rounded(width), height: rounded(height) },
    materials: materialNames, wheel_pivots_m: wheelPivots,
    sha256: createHash('sha256').update(bytes).digest('hex'),
    validator: {
      version: validator.version(), errors: result.issues.numErrors,
      warnings: result.issues.numWarnings, infos: result.issues.numInfos,
      hints: result.issues.numHints,
    },
  };
}

const models = [];
for (const spec of specs) models.push(await validate(spec));
const manifest = new URL('models.json', folder);
const temporary = new URL('.models.json.tmp', folder);
await writeFile(temporary, JSON.stringify(models, null, 2)+'\n', { flag: 'wx' });
await rename(temporary, manifest);

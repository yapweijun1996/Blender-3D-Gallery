import assert from 'node:assert/strict';
import fs from 'node:fs';
import { fileURLToPath } from 'node:url';
import { createHash } from 'node:crypto';
import { Box3, Vector3 } from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import validator from 'gltf-validator';

const dir = fileURLToPath(new URL('.', import.meta.url));
const spec = JSON.parse(fs.readFileSync(dir + 'backlog.json'));
const edited = process.argv[2];
const bytes = fs.readFileSync(edited ?? dir + 'exports/optimized.glb');
const json = JSON.parse(bytes.subarray(20, 20 + bytes.readUInt32LE(12)));
const validation = await validator.validateBytes(new Uint8Array(bytes), { uri: 'optimized.glb', maxIssues: 100 });
if (!edited) fs.writeFileSync(dir + 'reports/khronos.json', JSON.stringify(validation, null, 2) + '\n');
assert.equal(validation.issues.numErrors, 0);
assert.equal(validation.issues.numWarnings, 0);
assert.ok(json.buffers.every(b => !b.uri));
for (const field of ['images', 'textures', 'cameras', 'animations', 'skins']) assert.equal(json[field]?.length ?? 0, 0, field);
assert.ok(!json.extensions?.KHR_lights_punctual);
assert.equal(json.materials.length, 3);
assert.ok(json.materials.every(m => (m.alphaMode ?? 'OPAQUE') === 'OPAQUE'));
assert.equal(json.meshes.length, 7);
const gltf = await new GLTFLoader().parseAsync(bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength), '');
gltf.scene.updateMatrixWorld(true);
const root = gltf.scene.getObjectByName(spec.root);
assert.ok(root);
assert.deepEqual(root.position.toArray(), [0, 0, 0]);
assert.equal(root.userData.units, 'metres');
assert.equal(root.userData.seats, 4);
assert.equal(root.userData.front_axis, 'Blender -Y / glTF +Z');
assert.equal(root.children.length, 7);
let triangles = 0, vertices = 0, drawCalls = 0;
const parts = {};
const a = new Vector3(), b = new Vector3(), c = new Vector3();
root.traverse(o => {
  if (!o.isMesh) return;
  drawCalls++;
  const p = o.geometry.attributes.position, n = o.geometry.attributes.normal, index = o.geometry.index;
  assert.ok(n);
  assert.ok([...p.array, ...n.array].every(Number.isFinite));
  vertices += p.count;
  const count = index?.count ?? p.count;
  triangles += count / 3;
  for (let i = 0; i < count; i += 3) {
    a.fromBufferAttribute(p, index ? index.getX(i) : i);
    b.fromBufferAttribute(p, index ? index.getX(i + 1) : i + 1);
    c.fromBufferAttribute(p, index ? index.getX(i + 2) : i + 2);
    assert.ok(b.sub(a).cross(c.sub(a)).lengthSq() > 1e-20, `${o.name}: degenerate triangle`);
  }
});
for (const name of spec.features) {
  const group = root.getObjectByName(name + '_Geometry');
  assert.ok(group && group.parent === root, `Independent placement node: ${name}`);
  const box = new Box3().setFromObject(group, true);
  parts[name] = { pivot: group.position.toArray(), dimensions: box.getSize(new Vector3()).toArray(),
    min: box.min.toArray(), max: box.max.toArray(), source_parts: group.userData.source_parts };
  if (name === 'TableNumberStand') group.traverse(o => {
    if (o.isMesh && o.material.name === 'Warm ivory ceramic and blank card')
      parts[name].blank_card_width = new Box3().setFromObject(o, true).getSize(new Vector3()).x;
  });
}
const close = (a, b) => assert.ok(Math.abs(a - b) < 1e-5, `${a} != ${b}`);
parts.Table.dimensions.forEach((v, i) => close(v, [.8, .75, .8][i]));
close(parts.Table.min[1], 0);
for (const name of ['TableNumberStand', 'CondimentTray']) {
  close(parts[name].min[1], .75);
  assert.ok(parts[name].min[0] > -.4 && parts[name].max[0] < .4);
  assert.ok(parts[name].min[2] > -.4 && parts[name].max[2] < .4);
}
assert.ok(!new Box3(new Vector3(...parts.TableNumberStand.min), new Vector3(...parts.TableNumberStand.max))
  .intersectsBox(new Box3(new Vector3(...parts.CondimentTray.min), new Vector3(...parts.CondimentTray.max))));
const placement = [];
for (const name of spec.features.filter(n => n.startsWith('Chair_'))) {
  const part = parts[name];
  close(part.min[1], 0);
  assert.ok(part.max[1] > .79 && part.max[1] < .82);
  assert.ok(!new Box3(new Vector3(...part.min), new Vector3(...part.max))
    .intersectsBox(new Box3(new Vector3(...parts.Table.min), new Vector3(...parts.Table.max))), `${name}: table clearance`);
  const group = root.getObjectByName(name + '_Geometry');
  const position = group.position.clone(), quaternion = group.quaternion.clone();
  group.position.set(3, 0, 2);
  group.rotateY(Math.PI / 2);
  gltf.scene.updateMatrixWorld(true);
  const moved = new Box3().setFromObject(group, true);
  close(moved.min.y, 0);
  const table = new Box3().setFromObject(root.getObjectByName('Table_Geometry'), true);
  table.min.toArray().forEach((v, i) => close(v, parts.Table.min[i]));
  group.position.copy(position);
  group.quaternion.copy(quaternion);
  placement.push({ name, independent_move_rotate: 'PASS', floor_contact: moved.min.y });
}
gltf.scene.updateMatrixWorld(true);
const bounds = new Box3().setFromObject(gltf.scene, true);
close(bounds.min.y, 0);
close(bounds.min.x + bounds.max.x, 0);
close(bounds.min.z + bounds.max.z, 0);
assert.ok(bytes.length < spec.budget.bytes);
assert.ok(triangles <= spec.budget.triangles);
assert.ok(drawCalls <= spec.budget.mesh_primitives);
const report = { result: 'PASS', id: spec.slug, glb_bytes: bytes.length, triangles, vertices,
  placement_meshes: json.meshes.length, mesh_primitives: drawCalls, materials: json.materials.length,
  images: 0, animations: 0, dimensions: bounds.getSize(new Vector3()).toArray(),
  axis_order: 'glTF X,Y,Z (width,height,depth)', bounds: {min: bounds.min.toArray(), max: bounds.max.toArray()},
  sha256: createHash('sha256').update(bytes).digest('hex'), budget: spec.budget,
  validation: {errors: 0, warnings: 0}, parts, placement,
  checks: ['Measured 0.8 x 0.8 x 0.75 metre table', 'Four named floor-pivot chairs move and rotate independently',
    'Chairs clear the table; tabletop accessories contained and separated', 'Finite positions/normals; no degenerate triangles',
    'Three shared opaque materials; no textures or external resources'] };
if (!edited) fs.writeFileSync(dir + 'reports/assets.json', JSON.stringify(report, null, 2) + '\n');
else {
  const original = JSON.parse(fs.readFileSync(dir + 'reports/assets.json'));
  assert.notEqual(report.sha256, original.sha256);
  const hasRoughness = json.materials.some(m => Math.abs(m.pbrMetallicRoughness.roughnessFactor - .77) < 1e-5);
  assert.ok(hasRoughness);
  close(parts.TableNumberStand.blank_card_width / original.parts.TableNumberStand.blank_card_width, .92);
  for (const [name, part] of Object.entries(parts)) if (name !== 'TableNumberStand') {
    for (const key of ['min', 'max']) part[key].forEach((v, i) => close(v, original.parts[name][key][i]));
  }
  fs.writeFileSync(dir + 'reports/source-edit.json', JSON.stringify({result:'PASS', edited_sha256:report.sha256,
    blank_card_width_ratio:.92, roughness:.77, unrelated_placement_groups_unchanged:6, validation:report.validation}, null, 2) + '\n');
}
console.log(JSON.stringify({ result: report.result, triangles, bytes: bytes.length, draw_calls: drawCalls, materials: 3, dimensions: report.dimensions }));

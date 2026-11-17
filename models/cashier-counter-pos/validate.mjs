import assert from 'node:assert/strict';
import fs from 'node:fs';
import { fileURLToPath } from 'node:url';
import { createHash } from 'node:crypto';
import { Box3, Vector3 } from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import validator from 'gltf-validator';

const dir = fileURLToPath(new URL('.', import.meta.url));
const bytes = fs.readFileSync(dir + 'exports/optimized.glb');
const json = JSON.parse(bytes.subarray(20, 20 + bytes.readUInt32LE(12)));
const validation = await validator.validateBytes(new Uint8Array(bytes));
fs.writeFileSync(dir + 'reports/khronos.json', JSON.stringify(validation, null, 2) + '\n');
assert.equal(validation.issues.numErrors, 0);
assert.equal(validation.issues.numWarnings, 0);
assert.ok(json.buffers.every(b => !b.uri));
for (const key of ['images', 'textures', 'cameras', 'skins', 'animations']) assert.equal(json[key]?.length ?? 0, 0, key);
assert.ok(!json.extensions?.KHR_lights_punctual);
assert.equal(json.materials.length, 3);
assert.ok(json.materials.every(m => !m.alphaMode || m.alphaMode === 'OPAQUE'));
const gltf = await new GLTFLoader().parseAsync(bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength), '');
gltf.scene.updateMatrixWorld(true);
const root = gltf.scene.getObjectByName('ASSET_CashierCounterPOS');
assert.ok(root);
assert.deepEqual(root.position.toArray(), [0, 0, 0]);
assert.equal(root.userData.units, 'metres');
assert.equal(root.userData.front_axis, 'Blender -Y / glTF +Z');
let triangles = 0, primitives = 0, degenerate = 0;
const parts = [], a = new Vector3(), b = new Vector3(), c = new Vector3();
root.traverse(o => {
  if (!o.isMesh) return;
  primitives++;
  parts.push(...o.userData.source_parts);
  const g = o.geometry, p = g.attributes.position;
  assert.ok([...p.array].every(Number.isFinite));
  assert.ok(g.attributes.normal && [...g.attributes.normal.array].every(Number.isFinite));
  const count = g.index?.count ?? p.count;
  triangles += count / 3;
  for (let i = 0; i < count; i += 3) {
    a.fromBufferAttribute(p, g.index ? g.index.getX(i) : i);
    b.fromBufferAttribute(p, g.index ? g.index.getX(i + 1) : i + 1);
    c.fromBufferAttribute(p, g.index ? g.index.getX(i + 2) : i + 2);
    if (b.sub(a).cross(c.sub(a)).lengthSq() <= 1e-24) degenerate++;
  }
});
assert.equal(degenerate, 0);
assert.equal(primitives, 3);
for (const name of ['COUNTER_Countertop', 'POS_BlankDarkTouchscreen', 'CARD_Housing', 'CARD_BlankScreen',
  'PRINTER_Body', 'PRINTER_BlankReceipt', 'DRAWER_Front', 'BAG_Upright', 'BAG_Hook', 'SIGN_BlankFace'])
  assert.ok(parts.includes(name), name);
const bounds = new Box3().setFromObject(root, true);
const dimensions = bounds.getSize(new Vector3()).toArray();
assert.ok(Math.abs(dimensions[0] - 1.4) < 1e-6);
assert.ok(Math.abs(dimensions[2] - .7) < 1e-6);
assert.ok(dimensions[1] > 1.40 && dimensions[1] < 1.44);
assert.ok(Math.abs(bounds.min.y) < 1e-6);
assert.ok(Math.abs(bounds.max.x + bounds.min.x) < 1e-6);
assert.ok(Math.abs(bounds.max.z + bounds.min.z) < 1e-6);
const budget = {triangles:15000, bytes:1572864, mesh_primitives:3, materials:3};
assert.ok(triangles < budget.triangles && bytes.length < budget.bytes);
const report = {result:'PASS', id:'cashier-counter-pos', glb_bytes:bytes.length, triangles,
  mesh_primitives:primitives, meshes:json.meshes.length, materials:json.materials.length,
  dimensions_gltf_xyz_m:dimensions, bounds:{min:bounds.min.toArray(), max:bounds.max.toArray()},
  degenerate_triangles:degenerate, source_parts:parts.length, features:parts,
  budget, validation:{errors:validation.issues.numErrors, warnings:validation.issues.numWarnings, infos:validation.issues.numInfos},
  textures:0, animation_clips:0, sha256:createHash('sha256').update(bytes).digest('hex')};
fs.writeFileSync(dir + 'reports/assets.json', JSON.stringify(report, null, 2) + '\n');
console.log(JSON.stringify(report));

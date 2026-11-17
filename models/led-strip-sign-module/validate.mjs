import assert from 'node:assert/strict';
import fs from 'node:fs';
import { fileURLToPath } from 'node:url';
import { createHash } from 'node:crypto';
import { Box3, Vector3, Raycaster } from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import validator from 'gltf-validator';

const dir = fileURLToPath(new URL('.', import.meta.url));
const bytes = fs.readFileSync(dir + 'exports/optimized.glb');
const json = JSON.parse(bytes.subarray(20, 20 + bytes.readUInt32LE(12)));
const validation = await validator.validateBytes(new Uint8Array(bytes), { uri: 'optimized.glb', maxIssues: 100 });
fs.writeFileSync(dir + 'reports/khronos.json', JSON.stringify(validation, null, 2) + '\n');
assert.equal(validation.issues.numErrors, 0);
assert.equal(validation.issues.numWarnings, 0);
const gltf = await new GLTFLoader().parseAsync(bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength), '');
gltf.scene.updateMatrixWorld(true);
const root = gltf.scene.getObjectByName('ASSET_LedStripSignModule');
assert.ok(root);
assert.deepEqual(root.position.toArray(), [0, 0, 0]);
assert.equal(root.userData.units, 'metres');
assert.equal(root.userData.origin, 'floor centre');
const names = ['SIGN_BlankFace', 'SIGN_Housing', 'SIGN_LedStrip', 'SIGN_WallBracket'];
const meshes = [];
gltf.scene.traverse(o => { if (o.isMesh) meshes.push(o); });
assert.deepEqual(meshes.map(o => o.name).sort(), names);
assert.equal(json.materials.length, 3);
assert.equal(gltf.animations.length, 0);
for (const key of ['images', 'textures', 'cameras', 'skins']) assert.equal(json[key]?.length ?? 0, 0);
assert.ok(json.buffers.every(b => !b.uri));
assert.ok(!json.extensions?.KHR_lights_punctual);
const near = (actual, expected, label) => assert.ok(Math.abs(actual - expected) < 2e-6, `${label}: ${actual} != ${expected}`);
const parts = {};
let triangles = 0, vertices = 0, degenerates = 0;
for (const o of meshes) {
  const p = o.geometry.attributes.position;
  const n = o.geometry.attributes.normal;
  assert.ok(n);
  assert.ok([...p.array, ...n.array].every(Number.isFinite));
  const indices = o.geometry.index;
  const count = indices?.count ?? p.count;
  const a = new Vector3(), b = new Vector3(), c = new Vector3();
  for (let i = 0; i < count; i += 3) {
    a.fromBufferAttribute(p, indices ? indices.getX(i) : i);
    b.fromBufferAttribute(p, indices ? indices.getX(i + 1) : i + 1);
    c.fromBufferAttribute(p, indices ? indices.getX(i + 2) : i + 2);
    if (b.sub(a).cross(c.sub(a)).lengthSq() < 1e-20) degenerates++;
  }
  triangles += count / 3;
  vertices += p.count;
  const bounds = new Box3().setFromObject(o, true);
  parts[o.name] = { size: bounds.getSize(new Vector3()).toArray(), min: bounds.min.toArray(), max: bounds.max.toArray(), material: o.material.name };
}
assert.equal(degenerates, 0);
assert.ok(triangles < 6000);
assert.ok(bytes.length < 1572864);
const bounds = new Box3().setFromObject(gltf.scene, true);
const size = bounds.getSize(new Vector3()).toArray();
[2.4, .6, .145].forEach((value, i) => near(size[i], value, 'full bounds ' + i));
near(bounds.min.y, 0, 'floor datum');
near(bounds.min.x + bounds.max.x, 0, 'width centre');
near(bounds.min.z + bounds.max.z, 0, 'depth centre');
const enclosure = new Box3();
for (const name of ['SIGN_Housing', 'SIGN_BlankFace', 'SIGN_LedStrip']) enclosure.union(new Box3().setFromObject(root.getObjectByName(name), true));
const enclosureSize = enclosure.getSize(new Vector3()).toArray();
[2.4, .6, .12].forEach((value, i) => near(enclosureSize[i], value, 'enclosure ' + i));
const led = root.getObjectByName('SIGN_LedStrip');
assert.ok(json.nodes.some(node => node.name === 'SIGN_LedStrip' && json.meshes[node.mesh]?.name === 'SIGN_LedStrip'), 'public node and mesh names');
assert.ok(led.material.emissiveIntensity * led.material.emissive.r > 1, 'HDR emissive Bloom target');
for (const o of meshes.filter(o => o !== led)) assert.equal(o.material.emissive.getHex(), 0, 'only LED is emissive');
const recess = parts.SIGN_Housing.max[2] - parts.SIGN_LedStrip.max[2];
near(recess, .006, 'LED recessed below protective lip');
const ray = (mesh, x, y, direction = -1) => new Raycaster(new Vector3(x, y, direction < 0 ? 1 : -1), new Vector3(0, 0, direction)).intersectObject(mesh, false);
assert.equal(ray(led, 0, .3).length, 0, 'blank centre is not emissive');
for (const [x, y] of [[-1.141, .3], [1.141, .3], [0, .059], [0, .541]]) assert.ok(ray(led, x, y).length, 'continuous perimeter');
const faceHits = ray(root.getObjectByName('SIGN_BlankFace'), 0, .3);
assert.ok(faceHits.length && faceHits[0].face.normal.clone().transformDirection(root.getObjectByName('SIGN_BlankFace').matrixWorld).z > .99, 'front faces +Z');
const bracket = root.getObjectByName('SIGN_WallBracket');
for (const x of [-.75, .75]) for (const y of [.15, .45]) {
  assert.equal(ray(bracket, x, y, 1).length, 0, 'open wall-mount slot');
  assert.ok(ray(bracket, x + .06, y, 1).length, 'material beside slot');
}
near(parts.SIGN_WallBracket.max[2], parts.SIGN_Housing.min[2], 'bracket contacts rear housing');
const report = {
  result: 'PASS', id: 'led-strip-sign-module', glb_bytes: bytes.length, triangles, vertices,
  meshes: meshes.length, primitives: json.meshes.reduce((sum, mesh) => sum + mesh.primitives.length, 0),
  materials: json.materials.length, images: 0, animations: 0, degenerate_triangles: degenerates,
  dimensions: { units: 'metres', axis_order: 'width, height, depth (glTF X,Y,Z)', size, bounds: { min: bounds.min.toArray(), max: bounds.max.toArray() } },
  enclosure_size_m: enclosureSize, led_recess_m: recess,
  sha256: createHash('sha256').update(bytes).digest('hex'),
  validation: { errors: validation.issues.numErrors, warnings: validation.issues.numWarnings },
  verified: ['floor-centre origin', '+Z front normals', 'separate HDR emissive strip', 'continuous perimeter with blank centre', 'four open bracket slots', 'bracket rear contact'], parts,
};
fs.writeFileSync(dir + 'reports/assets.json', JSON.stringify(report, null, 2) + '\n');
const metadataPath = dir + 'metadata/led-strip-sign-module.json';
if (process.argv.includes('--update-metadata')) {
  const metadata = JSON.parse(fs.readFileSync(metadataPath));
  metadata.dimensions = report.dimensions;
  metadata.statistics = Object.fromEntries(['glb_bytes', 'triangles', 'vertices', 'meshes', 'primitives', 'materials', 'images', 'animations', 'sha256'].map(key => [key, report[key]]));
  metadata.interface.enclosure_size_m = enclosureSize;
  metadata.interface.led_recess_m = recess;
  metadata.interface.wall_plane_gltf_z = bounds.min.z;
  fs.writeFileSync(metadataPath, JSON.stringify(metadata, null, 2) + '\n');
} else if (fs.existsSync(metadataPath)) {
  const metadata = JSON.parse(fs.readFileSync(metadataPath));
  assert.deepEqual(metadata.dimensions, report.dimensions);
  for (const [key, value] of Object.entries(metadata.statistics)) assert.equal(value, report[key], 'measured metadata ' + key);
}
console.log(JSON.stringify({ result: report.result, triangles, bytes: bytes.length, meshes: meshes.length, materials: json.materials.length, size, led_recess_m: recess, khronos: report.validation }));

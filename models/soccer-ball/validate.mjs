import assert from 'node:assert/strict';
import fs from 'node:fs';
import { createHash } from 'node:crypto';
import { fileURLToPath } from 'node:url';
import { Box3, Vector3 } from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import validator from 'gltf-validator';

const dir = fileURLToPath(new URL('.', import.meta.url));
const spec = JSON.parse(fs.readFileSync(dir + 'backlog.json'));
const source = JSON.parse(fs.readFileSync(dir + 'reports/source-geometry.json'));
const bytes = fs.readFileSync(dir + 'exports/optimized.glb');
const json = JSON.parse(bytes.subarray(20, 20 + bytes.readUInt32LE(12)));
const validation = await validator.validateBytes(new Uint8Array(bytes), { maxIssues: 100 });
fs.writeFileSync(dir + 'reports/khronos.json', JSON.stringify(validation, null, 2) + '\n');
assert.equal(validation.issues.numErrors, 0);
assert.equal(validation.issues.numWarnings, 0);
// One embedded tangent-space normal map for the pebbled grain; nothing external, no cameras or lights.
assert.equal(json.images?.length, 1);
assert.equal(json.textures?.length, 1);
assert.ok(json.images.every(image => image.bufferView !== undefined && image.uri === undefined));
assert.ok(!json.cameras?.length && !json.extensions?.KHR_lights_punctual);
assert.ok(json.buffers.every(buffer => buffer.uri === undefined));
for (const m of json.materials) assert.equal(m.pbrMetallicRoughness.metallicFactor ?? 1, 0);
assert.ok(json.materials.filter(m=>m.name.startsWith('Panel ')).every(m=>m.normalTexture));
assert.ok(json.images.every(i=>i.mimeType==='image/jpeg'));
// Node has no image decoder: parse geometry from a copy without the texture binding.
const jsonLength = bytes.readUInt32LE(12);
const bin = bytes.subarray(28 + jsonLength, 28 + jsonLength + bytes.readUInt32LE(20 + jsonLength));
const geometryJson = structuredClone(json);
delete geometryJson.images;
delete geometryJson.textures;
delete geometryJson.samplers;
for (const material of geometryJson.materials) delete material.normalTexture;
const jsonChunk = Buffer.from(JSON.stringify(geometryJson));
const paddedJson = Buffer.alloc(Math.ceil(jsonChunk.length / 4) * 4, 0x20);
jsonChunk.copy(paddedJson);
const binHeader = Buffer.alloc(8);
binHeader.writeUInt32LE(bin.length, 0);
binHeader.writeUInt32LE(0x004e4942, 4);
const header = Buffer.alloc(20);
header.writeUInt32LE(0x46546c67, 0);
header.writeUInt32LE(2, 4);
header.writeUInt32LE(20 + paddedJson.length + 8 + bin.length, 8);
header.writeUInt32LE(paddedJson.length, 12);
header.writeUInt32LE(0x4e4f534a, 16);
const geometryGlb = Buffer.concat([header, paddedJson, binHeader, bin]);
const gltf = await new GLTFLoader().parseAsync(geometryGlb.buffer.slice(geometryGlb.byteOffset, geometryGlb.byteOffset + geometryGlb.byteLength), '');
gltf.scene.updateMatrixWorld(true);
const root = gltf.scene.getObjectByName(spec.root);
assert.ok(root);
assert.deepEqual(root.position.toArray(), [0, 0, 0]);
assert.equal(root.userData.units, 'metres');
assert.equal(root.userData.up_axis, 'Blender +Z / glTF +Y');
assert.equal(root.userData.front_axis, 'Blender -Y / glTF +Z');
assert.equal(gltf.animations.length, 0);

const R = source.radius_m;
const centre = new Vector3(0, source.centre_height_m, 0);
const byMaterial = new Map();
let meshes = 0, primitives = 0, triangles = 0, vertices = 0;
gltf.scene.traverse(object => {
  if (!object.isMesh) return;
  meshes++;
  const geometry = object.geometry;
  const positions = geometry.attributes.position;
  assert.ok(geometry.attributes.normal && geometry.attributes.uv);
  for (const attribute of Object.values(geometry.attributes)) assert.ok([...attribute.array].every(Number.isFinite));
  const list = [];
  for (let i = 0; i < positions.count; i++) list.push(new Vector3().fromBufferAttribute(positions, i).applyMatrix4(object.matrixWorld));
  const index = geometry.index, count = index?.count ?? positions.count;
  const tris = [];
  const edgeA = new Vector3(), edgeB = new Vector3();
  for (let i = 0; i < count; i += 3) {
    const t = [0, 1, 2].map(k => index ? index.getX(i + k) : i + k);
    assert.ok(edgeA.subVectors(list[t[1]], list[t[0]]).cross(edgeB.subVectors(list[t[2]], list[t[0]])).lengthSq() > 1e-20, 'nondegenerate triangle');
    tris.push(t);
  }
  byMaterial.set(object.material.name, { list, tris });
  triangles += count / 3;
  vertices += positions.count;
  primitives++;
});
assert.equal(primitives, 4);
assert.equal(json.meshes.length, 1);
assert.equal(json.materials.length, 4);
assert.ok(triangles <= spec.budget.triangles);
assert.ok(bytes.length <= spec.budget.bytes);

const bounds = new Box3().setFromObject(gltf.scene, true);
const dimensions = bounds.getSize(new Vector3()).toArray();
assert.ok(Math.abs(bounds.min.y) < 1e-6, 'actual floor contact');
assert.ok(Math.abs(bounds.min.x + bounds.max.x) < 0.0005 && Math.abs(bounds.min.z + bounds.max.z) < 0.0005, 'centred in X/Z');
// Tessellation and edge rounding may reduce sampled extents by at most 0.8 mm.
for (const d of dimensions) assert.ok(Math.abs(d-2*R)<0.0008, 'standard midpoint diameter within 0.8 mm');
const expected = {'soccer-ball':[0.69,32,12,20], 'volleyball':[0.66,18,6,12], 'handball':[0.59,32,12,20], 'netball':[0.70,18,6,12], 'water-polo-ball':[0.695,18,6,12]}[spec.slug];
assert.ok(Math.abs(2*Math.PI*R-expected[0])<1e-8);
const accent=byMaterial.get('Panel accent'), main=byMaterial.get('Panel main'), bed=byMaterial.get('Recessed seam bed');
assert.ok(accent && main && bed);
for (const patch of [accent,main]) {
  assert.ok(patch.list.every(p=>p.distanceTo(centre) <= R+1e-6 && p.distanceTo(centre)>=R-source.channel_depth_m-1e-6));
  assert.ok(patch.list.some(p=>p.distanceTo(centre)>R-0.0001), 'puffed skin');
  assert.ok(patch.list.some(p=>p.distanceTo(centre)<R-source.channel_depth_m+0.0001), 'real recessed edges');
}
assert.ok(bed.list.every(p=>Math.abs(p.distanceTo(centre)-(R-source.channel_depth_m))<1e-6), 'recessed spherical bed');
if (spec.slug==='soccer-ball') {
  const thread=byMaterial.get('Recessed stitching');
  assert.equal(components(thread),450,'450 separate recessed thread bridges');
  assert.equal(thread.tris.length,5400);
  assert.ok(thread.list.every(p=>p.distanceTo(centre)<R-0.0004));
  const dark=json.materials.find(m=>m.name==='Panel accent').pbrMetallicRoughness.baseColorFactor;
  const light=json.materials.find(m=>m.name==='Panel main').pbrMetallicRoughness.baseColorFactor;
  assert.ok(dark.slice(0,3).every(c=>c<0.02) && light.slice(0,3).every(c=>c>0.6),'black pentagons / white hexagons');
}

function components({ list, tris }) {
  const key = v => v.toArray().map(x => Math.round(x * 1e6)).join(',');
  const ids = list.map(key), parent = new Map(ids.map(id => [id, id]));
  const find = a => { while (parent.get(a) !== a) { parent.set(a, parent.get(parent.get(a))); a = parent.get(a); } return a; };
  for (const [a, b, c] of tris) { parent.set(find(ids[b]), find(ids[a])); parent.set(find(ids[c]), find(ids[a])); }
  return new Set(ids.map(find)).size;
}
const accentPanels=components(accent), mainPanels=components(main);
assert.equal(accentPanels,expected[2]); assert.equal(mainPanels,expected[3]);
const panels=accentPanels+mainPanels;
assert.equal(panels,expected[1], 'exact separate skin components');
assert.ok(primitives<=spec.budget.mesh_primitives && json.materials.length<=spec.budget.materials && json.textures.length<=spec.budget.textures);

const report = {
  result: 'PASS', id: spec.slug, glb_bytes: bytes.length, triangles, vertices, meshes, primitives,
  materials: json.materials.length, textures: json.textures.length, animations: gltf.animations.length,
  dimensions_m: dimensions, bounds_m: { min: bounds.min.toArray(), max: bounds.max.toArray() },
  diameter_m: 2 * R, circumference_m: source.circumference_m, channel_width_m: source.channel_width_m, channel_depth_m: source.channel_depth_m,
  panels, panel_material_counts: [accentPanels,mainPanels],
  sha256: createHash('sha256').update(bytes).digest('hex'), budget: spec.budget,
  validation: { errors: validation.issues.numErrors, warnings: validation.issues.numWarnings, infos: validation.issues.numInfos },
};
fs.writeFileSync(dir + 'reports/assets.json', JSON.stringify(report, null, 2) + '\n');
console.log(JSON.stringify(report, null, 2));

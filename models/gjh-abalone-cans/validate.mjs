import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { createHash } from 'node:crypto';
import { Box3, Vector3 } from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import validator from 'gltf-validator';

// Validates each exported can, then records measured metrics in its metadata and reports/assets.json.
const root = path.dirname(fileURLToPath(import.meta.url));
const cans = [
  ['gjh-can-new-zealand-abalone', 'ASSET_GJHCanNewZealandAbalone'],
  ['gjh-can-australia-abalone', 'ASSET_GJHCanAustraliaAbalone'],
  ['gjh-can-south-africa-abalone', 'ASSET_GJHCanSouthAfricaAbalone'],
  ['gjh-can-mexico-abalone', 'ASSET_GJHCanMexicoAbalone'],
];
const parts = ['GoldRim', 'SilverMetal', 'Label'];
// GLTFLoader needs a browser to decode textures, so geometry is checked on a texture-stripped copy.
function stripTextures(bytes) {
  const jsonLength = bytes.readUInt32LE(12);
  const doc = JSON.parse(bytes.subarray(20, 20 + jsonLength));
  delete doc.images; delete doc.textures; delete doc.samplers;
  for (const m of doc.materials ?? []) delete m.pbrMetallicRoughness?.baseColorTexture;
  const chunk = Buffer.from(JSON.stringify(doc)); const padded = Buffer.concat([chunk, Buffer.alloc(-chunk.length & 3, 0x20)]);
  const rest = bytes.subarray(20 + jsonLength);
  const out = Buffer.alloc(20 + padded.length + rest.length);
  out.write('glTF', 0, 'ascii'); out.writeUInt32LE(2, 4); out.writeUInt32LE(out.length, 8);
  out.writeUInt32LE(padded.length, 12); out.write('JSON', 16, 'ascii'); padded.copy(out, 20); rest.copy(out, 20 + padded.length);
  return out;
}
async function checkLod1(id, rootName, build, textureBytes, lod0Triangles) {
  const bytes = fs.readFileSync(path.join(root, 'exports/lod1', id + '-lod1.glb'));
  const validation = await validator.validateBytes(new Uint8Array(bytes), { uri: id + '-lod1.glb' });
  if (validation.issues.numErrors || validation.issues.numWarnings) throw Error(id + ' LOD1: ' + JSON.stringify(validation.issues));
  const json = JSON.parse(bytes.subarray(20, 20 + bytes.readUInt32LE(12)));
  if (json.images?.length !== 1 || json.buffers.some(b => b.uri)) throw Error(id + ' LOD1: expected one embedded texture');
  const bare = stripTextures(bytes);
  const gltf = await new GLTFLoader().parseAsync(bare.buffer.slice(bare.byteOffset, bare.byteOffset + bare.byteLength), '');
  gltf.scene.updateMatrixWorld(true);
  const asset = gltf.scene.getObjectByName(rootName);
  const bounds = new Box3().setFromObject(asset);
  let triangles = 0, primitives = 0;
  asset.traverse(o => { if (o.isMesh) { primitives++; triangles += (o.geometry.index?.count ?? o.geometry.attributes.position.count) / 3; } });
  const full = JSON.parse(fs.readFileSync(path.join(root, 'metadata', id + '.json'), 'utf8'));
  if (Math.abs(bounds.min.y) > 0.0005 || triangles >= lod0Triangles || primitives > 3)
    throw Error(`${id} LOD1: origin/budget violation (${triangles} triangles, ${primitives} primitives)`);
  return { glb_bytes: bytes.length, triangles, draw_calls: primitives, materials: json.materials.length,
    texture_pixels: build.lod1.texture, texture_memory_bytes: textureBytes(build.lod1.texture),
    dimensions: bounds.getSize(new Vector3()).toArray(), sha256: createHash('sha256').update(bytes).digest('hex'),
    validation: { errors: validation.issues.numErrors, warnings: validation.issues.numWarnings } };
}
const reports = [];
for (const [id, rootName] of cans) {
  const bytes = fs.readFileSync(path.join(root, 'exports', id + '.glb'));
  const validation = await validator.validateBytes(new Uint8Array(bytes), { uri: id + '.glb' });
  if (validation.issues.numErrors || validation.issues.numWarnings) throw Error(id + ': ' + JSON.stringify(validation.issues));
  const json = JSON.parse(bytes.subarray(20, 20 + bytes.readUInt32LE(12)));
  if (json.buffers.some(b => b.uri) || json.images?.length !== 1 || json.images[0].mimeType !== 'image/jpeg')
    throw Error(id + ': expected a self-contained GLB with exactly one embedded JPEG label texture');
  const bare = stripTextures(bytes);
  const gltf = await new GLTFLoader().parseAsync(bare.buffer.slice(bare.byteOffset, bare.byteOffset + bare.byteLength), '');
  gltf.scene.updateMatrixWorld(true);
  const asset = gltf.scene.getObjectByName(rootName);
  if (!asset) throw Error(id + ': missing root ' + rootName);
  const bounds = new Box3().setFromObject(asset);
  let triangles = 0, vertices = 0, primitives = 0;
  const names = new Set();
  asset.traverse(o => {
    if (o.name) names.add(o.name);
    if (!o.isMesh) return;
    primitives++;
    vertices += o.geometry.attributes.position.count;
    triangles += (o.geometry.index?.count ?? o.geometry.attributes.position.count) / 3;
  });
  for (const part of parts) if (![...names].some(n => n === part || n.startsWith(part + '_'))) throw Error(id + ': missing part ' + part);
  const label = asset.getObjectByName('Label');
  let uvOk = false;
  label.traverse(o => { if (o.isMesh && o.geometry.attributes.uv) uvOk = true; });
  if (!uvOk) throw Error(id + ': Label has no UVs');
  const size = bounds.getSize(new Vector3());
  if (Math.abs(bounds.min.y) > 0.0005 || size.x < 0.07 || size.x > 0.08 || size.y < 0.11 || size.y > 0.13 || bytes.length > 500 * 1024 || triangles > 5000 || primitives > 3 || json.materials.length > 3)
    throw Error(`${id}: budget/origin violation ${bytes.length} bytes, ${triangles} triangles, ${primitives} primitives, size ${size.toArray()}`);
  const build = JSON.parse(fs.readFileSync(path.join(root, 'reports/build.json'), 'utf8')).cans[id];
  const textureBytes = ([w, h]) => Math.round(w * h * 4 * 4 / 3); // RGBA8 with a full mip chain on the GPU
  const metrics = { glb_bytes: bytes.length, triangles, vertices, primitives, materials: json.materials.length, textures: json.images.length,
    texture_pixels: null, animations: (json.animations ?? []).length, dimensions: size.toArray(),
    bounds: { min: bounds.min.toArray(), max: bounds.max.toArray() }, sha256: createHash('sha256').update(bytes).digest('hex') };
  metrics.texture_pixels = build.texture;
  metrics.draw_calls = primitives;
  metrics.texture_memory_bytes = textureBytes(build.texture);
  metrics.lod1 = await checkLod1(id, rootName, build, textureBytes, triangles);
  const check = { errors: validation.issues.numErrors, warnings: validation.issues.numWarnings, validator: validation.validatorVersion };
  const file = path.join(root, 'metadata', id + '.json');
  const meta = JSON.parse(fs.readFileSync(file, 'utf8'));
  meta.metrics = metrics;
  meta.validation = check;
  fs.writeFileSync(file, JSON.stringify(meta, null, 2) + '\n');
  reports.push({ id, ...metrics, validation: check });
}
fs.mkdirSync(path.join(root, 'reports'), { recursive: true });
fs.writeFileSync(path.join(root, 'reports/assets.json'), JSON.stringify(reports, null, 2) + '\n');
for (const r of reports) console.log(r.id, r.glb_bytes, 'bytes', r.triangles, 'tris', r.dimensions.map(v => +v.toFixed(4)).join(' x '), 'errors', r.validation.errors, 'warnings', r.validation.warnings);

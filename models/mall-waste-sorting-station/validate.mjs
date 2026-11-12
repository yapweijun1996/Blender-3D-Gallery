import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { createHash } from 'node:crypto';
import { Box3, Vector3 } from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import validator from 'gltf-validator';

const root = path.dirname(fileURLToPath(import.meta.url));
const id = 'mall-waste-sorting-station';
const bytes = fs.readFileSync(path.join(root, 'exports', id + '.glb'));
const validation = await validator.validateBytes(new Uint8Array(bytes), { uri: id + '.glb' });
if (validation.issues.numErrors || validation.issues.numWarnings) throw Error(JSON.stringify(validation.issues));
const json = JSON.parse(bytes.subarray(20, 20 + bytes.readUInt32LE(12)));
if (json.images?.length || json.buffers.some(b => b.uri)) throw Error('Expected self-contained texture-free GLB');
const gltf = await new GLTFLoader().parseAsync(bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength), '');
gltf.scene.updateMatrixWorld(true);
const bounds = new Box3().setFromObject(gltf.scene);
const assetRoot = gltf.scene.getObjectByName('ASSET_MallWasteSortingStation');
const groups = ['StationFrame', 'RecycleCompartment', 'FoodCompartment', 'GeneralCompartment', 'RecycleLid', 'FoodLid', 'GeneralLid'];
let triangles = 0, vertices = 0, primitives = 0;
const nodes = [];
gltf.scene.traverse(o => {
  if (o.name) nodes.push(o.name);
  if (!o.isMesh) return;
  primitives++;
  vertices += o.geometry.attributes.position.count;
  triangles += (o.geometry.index?.count ?? o.geometry.attributes.position.count) / 3;
});
for (const name of groups) {
  const group = gltf.scene.getObjectByName(name);
  let mesh = false;
  group?.traverse(o => { mesh ||= Boolean(o.isMesh && o.geometry.attributes.position.count > 0); });
  if (!group || !mesh || group.parent !== assetRoot) throw Error(name + ' must be an independent mesh-bearing root child');
}
// Independent compartments and lids deliberately retain their material slots.
if (Math.abs(bounds.min.y) > .001 || triangles > 20000 || bytes.length > 700000 || primitives > 26)
  throw Error(`Budget/origin violation: ${bytes.length} bytes, ${triangles} triangles, ${primitives} primitives`);
const report = { id, glb_bytes: bytes.length, triangles, vertices, primitives, materials: json.materials.length,
  animations: (json.animations ?? []).length, dimensions: bounds.getSize(new Vector3()).toArray(),
  bounds: { min: bounds.min.toArray(), max: bounds.max.toArray() }, nodes,
  sha256: createHash('sha256').update(bytes).digest('hex'),
  validation: { errors: validation.issues.numErrors, warnings: validation.issues.numWarnings, validator: validation.validatorVersion } };
fs.mkdirSync(path.join(root, 'reports'), { recursive: true });
fs.writeFileSync(path.join(root, 'reports/assets.json'), JSON.stringify(report, null, 2) + '\n');
console.log(JSON.stringify(report, null, 2));

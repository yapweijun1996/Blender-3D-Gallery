import assert from 'node:assert/strict';
import fs from 'node:fs';
import { createHash } from 'node:crypto';
import { fileURLToPath } from 'node:url';
import { Box3, Vector3, Raycaster } from 'three';
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
assert.ok((json.images??[]).every(i=>i.bufferView!==undefined && i.uri===undefined && i.mimeType==='image/jpeg'));
assert.ok((json.textures?.length??0)<=spec.budget.textures);
assert.ok(!json.cameras?.length && !json.extensions?.KHR_lights_punctual);
assert.ok(json.buffers.every(b=>b.uri===undefined));
for(const m of json.materials)assert.equal(m.pbrMetallicRoughness.metallicFactor,0);
// Node has no image decoder: parse geometry from a copy without the texture binding.
const jsonLength = bytes.readUInt32LE(12);
const bin = bytes.subarray(28 + jsonLength, 28 + jsonLength + bytes.readUInt32LE(20 + jsonLength));
const geometryJson = structuredClone(json);
delete geometryJson.images;
delete geometryJson.textures;
delete geometryJson.samplers;
for (const material of geometryJson.materials) { delete material.normalTexture; delete material.pbrMetallicRoughness?.baseColorTexture; }
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
assert.equal(root.userData.front_axis, 'Blender -Y / glTF +Z');
assert.equal(root.userData.up_axis, 'Blender +Z / glTF +Y');
assert.equal(json.meshes.length,1,'one evaluated export mesh');
assert.equal(gltf.animations.length, 0);

const byMaterial = new Map();
let meshes = 0, primitives = 0, triangles = 0, vertices = 0;
gltf.scene.traverse(object => {
  if (!object.isMesh) return;
  meshes++;
  const geometry = object.geometry;
  const positions = geometry.attributes.position;
  assert.ok(geometry.attributes.normal); if(object.material.normalMap)assert.ok(geometry.attributes.uv);
  for(const attr of Object.values(geometry.attributes))assert.ok([...attr.array].every(Number.isFinite),'finite attributes');
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
  if(!object.name.includes('VALVE_')) byMaterial.set(object.material.name, { list, tris });
  triangles += count / 3;
  vertices += positions.count;
  primitives++;
});

assert.ok(primitives <= spec.budget.mesh_primitives);
assert.ok(json.materials.length <= spec.budget.materials);
assert.ok(triangles <= spec.budget.triangles && bytes.length <= spec.budget.bytes);
const bounds = new Box3().setFromObject(gltf.scene, true);
const dimensions = bounds.getSize(new Vector3()).toArray();
const expected=[source.diameter_m,source.height_m,source.diameter_m];
for(let i=0;i<3;i++) assert.ok(Math.abs(dimensions[i]-expected[i])<source.diameter_m*.008, 'real-scale dimensions within 0.8%, tessellation/valve allowance');
assert.ok(Math.abs(bounds.min.y)<source.diameter_m*.003, 'floor contact');
assert.ok(Math.abs(bounds.min.x+bounds.max.x)<source.diameter_m*.003 && Math.abs(bounds.min.z+bounds.max.z)<source.diameter_m*.003,'centred X/Z');
const centre=new Vector3(0,source.diameter_m/2+(source.floor_shift_m??0),0);
const meshesForRay=[];gltf.scene.traverse(o=>{if(o.isMesh)meshesForRay.push(o);});
function raySurface(p,d) {
 const ray=new Raycaster(p.clone().addScaledVector(d,.1),d.clone().negate(),0,1);
 const hits=ray.intersectObjects(meshesForRay,false);assert.ok(hits.length,'surface hit');return hits[0].point;
}
const features={};
if(spec.slug==='golf-ball') {
 assert.equal(source.dimple_centres_gltf.length,362);let count=0;
 for(const a of source.dimple_centres_gltf){const p=new Vector3(...a),dir=p.clone().sub(centre).normalize();const hit=raySurface(p,dir);assert.ok(hit.distanceTo(centre)<source.diameter_m/2-.00012,'real recessed dimple');count++;}
 const cover=byMaterial.get('White urethane'), neighbours=cover.list.map(()=>new Set());
 for(const tri of cover.tris)for(const a of tri)for(const b of tri)if(a!==b)neighbours[a].add(b);
 const radii=cover.list.map(p=>p.distanceTo(centre));
 const minima=radii.filter((r,i)=>neighbours[i].size>0 && [...neighbours[i]].every(j=>radii[j]>r+1e-6)).length;
 assert.equal(minima,362,'independently counted geometric dimple minima');
 assert.equal(new Set(source.dimple_centres_gltf.map(p=>p.join(','))).size,362);
 features.dimples=minima;
}
if(spec.slug==='bowling-ball') {
 assert.equal(source.holes.length,3);let count=0;
 for(const hole of source.holes){const p=new Vector3(...hole.surface),dir=new Vector3(...hole.direction);const hit=raySurface(p,dir);assert.ok(p.clone().sub(hit).dot(dir)>hole.depth_m*.85,'real drilled hole depth');
 const tangent=dir.clone().cross(new Vector3(1,0,0)).normalize();const edge=p.clone().addScaledVector(tangent,hole.radius_m*1.5);const rim=raySurface(edge,dir);assert.ok(rim.distanceTo(centre)>source.diameter_m/2-.003,'skin around hole');count++;}
 features.hole_openings=count;
 assert.ok(json.materials.find(m=>m.name==='Two colour reactive resin').pbrMetallicRoughness.baseColorTexture,'baked swirl');
}
function components({ list, tris }) {
  const key = v => v.toArray().map(x => Math.round(x * 1e6)).join(',');
  const ids = list.map(key), parent = new Map(ids.map(id => [id, id]));
  const find = a => { while (parent.get(a) !== a) { parent.set(a, parent.get(parent.get(a))); a = parent.get(a); } return a; };
  for (const [a, b, c] of tris) { parent.set(find(ids[b]), find(ids[a])); parent.set(find(ids[c]), find(ids[a])); }
  return new Set(ids.map(find)).size;
}

if(spec.slug==='beach-ball'){
 const gores=[...byMaterial.keys()].filter(n=>n.startsWith('GORE_'));assert.equal(gores.length,6);
 for(const n of gores)assert.equal(components(byMaterial.get(n)),1,'one connected gore per colour');
 const caps=components(byMaterial.get('CAP_White'));assert.equal(caps,2,'two separate polar caps');features.coloured_gores=gores.length;features.white_caps=caps;
 assert.ok(meshesForRay.some(o=>o.name.includes('InflationPlug')));
}
if(spec.slug==='medicine-ball'){
 assert.ok(meshesForRay.some(o=>o.name.includes('Fill')));assert.equal(json.materials.filter(m=>m.normalTexture).length,2);features.fill_valves=1;
}
if(spec.slug==='ice-hockey-puck'){
 assert.ok(json.materials[0].normalTexture);assert.equal(source.knurled_band,true);features.knurled_band=true;
}
const report={result:'PASS',id:spec.slug,glb_bytes:bytes.length,triangles,vertices,meshes,primitives,materials:json.materials.length,textures:json.textures?.length??0,animations:gltf.animations.length,diameter_m:source.diameter_m,height_m:source.height_m,dimensions_m:dimensions,bounds_m:{min:bounds.min.toArray(),max:bounds.max.toArray()},features,sha256:createHash('sha256').update(bytes).digest('hex'),budget:spec.budget,validation:{errors:validation.issues.numErrors,warnings:validation.issues.numWarnings}};
fs.writeFileSync(dir+'reports/assets.json',JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report,null,2));

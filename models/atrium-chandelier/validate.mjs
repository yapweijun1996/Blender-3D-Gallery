// Delivery gate adapted from models/self-checkout-machine/validate.mjs.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {createHash} from 'node:crypto';
import {Box3, Vector3} from 'three';
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';
import validator from 'gltf-validator';

const bytes = fs.readFileSync(new URL('exports/optimized.glb', import.meta.url));
const json = JSON.parse(bytes.subarray(20, 20+bytes.readUInt32LE(12)));
const validation = await validator.validateBytes(new Uint8Array(bytes), {maxIssues: 1000});
fs.writeFileSync(new URL('reports/khronos.json', import.meta.url), JSON.stringify(validation, null, 2)+'\n');
assert.equal(validation.issues.numErrors, 0);
assert.equal(validation.issues.numWarnings, 0);
assert.ok(json.buffers.every(b => !b.uri));
for (const key of ['images', 'textures', 'animations', 'cameras']) assert.ok(!json[key]?.length, key);
assert.ok(!json.extensions?.KHR_lights_punctual);
assert.equal(json.materials.length, 3);
for (const m of json.materials) {
  assert.ok(!m.doubleSided);
  assert.ok(!m.alphaMode || m.alphaMode === 'OPAQUE');
  assert.ok(!m.extensions?.KHR_materials_transmission);
}
const gltf = await new GLTFLoader().parseAsync(bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset+bytes.byteLength), '');
gltf.scene.updateMatrixWorld(true);
const root = gltf.scene.getObjectByName('ASSET_AtriumChandelier');
assert.ok(root);
assert.deepEqual(root.position.toArray(), [0, 0, 0]);
assert.equal(root.userData.units, 'metres');
assert.equal(root.userData.origin, 'floor centre');
assert.equal(gltf.scene.children.length, 1);
const bounds = new Box3().setFromObject(root, true);
const dimensions = bounds.getSize(new Vector3()).toArray();
for (let i=0; i<3; i++) assert.ok(Math.abs(dimensions[i]-[3, 2, 3][i]) < 1e-6);
assert.ok(Math.abs(bounds.min.y) < 1e-7);
assert.ok(Math.abs(bounds.min.x+bounds.max.x) < 1e-7);
assert.ok(Math.abs(bounds.min.z+bounds.max.z) < 1e-7);
let triangles=0, vertices=0, minimumArea=Infinity;
const parts=[];
root.traverse(o => {
  if (!o.isMesh) return;
  const {position, normal} = o.geometry.attributes;
  assert.ok(position && normal);
  for (const a of [position, normal]) assert.ok([...a.array].every(Number.isFinite));
  const ids=o.geometry.index, count=ids?.count ?? position.count;
  for (let i=0; i<position.count; i++) assert.ok(Math.abs(new Vector3().fromBufferAttribute(normal,i).length()-1) < 1e-5);
  for (let i=0; i<count; i+=3) {
    const [a,b,c]=[0,1,2].map(j => new Vector3().fromBufferAttribute(position,ids ? ids.getX(i+j) : i+j));
    const area=b.sub(a).cross(c.sub(a)).length()/2;
    assert.ok(area > 1e-10, `nondegenerate triangle in ${o.name}`);
    minimumArea=Math.min(minimumArea,area);
  }
  triangles+=count/3;
  vertices+=position.count;
  parts.push({name:o.name, material:o.material.name, triangles:count/3});
});
assert.deepEqual(parts.map(p=>p.name).sort(), ['CRYSTAL_Pendants','FRAME_Chandelier','LIGHT_Ring']);
assert.equal(json.meshes.length, 3);
assert.ok(triangles < 20000);
assert.ok(bytes.length < 1.5*1024*1024);
const light = root.getObjectByName('LIGHT_Ring');
const lp=light.geometry.attributes.position;
const tiers=[{radius:1.445,height:1.23},{radius:1.025,height:1.02},{radius:.605,height:.8}];
const tierCounts=[0,0,0];
for (let i=0;i<lp.count;i++) {
  const v=new Vector3().fromBufferAttribute(lp,i).applyMatrix4(light.matrixWorld);
  const t=tiers.findIndex(t=>Math.abs(v.y-t.height)<.057 && Math.abs(Math.hypot(v.x,v.z)-t.radius)<.056);
  assert.ok(t>=0,'every LED vertex belongs to one concentric tier');
  tierCounts[t]++;
}
assert.ok(tierCounts.every(n=>n>0));
assert.ok(light.material.emissive.r >= light.material.emissive.g && light.material.emissive.g > light.material.emissive.b);
assert.ok(light.material.emissiveIntensity >= 3);
for (const name of ['FRAME_Chandelier','CRYSTAL_Pendants']) assert.equal(root.getObjectByName(name).material.emissive.getHex(),0);
// Weld split normal vertices, then count actual connected pendant surfaces.
const pendant=root.getObjectByName('CRYSTAL_Pendants');
const p=pendant.geometry.attributes.position, pi=pendant.geometry.index;
const keys=new Map(), ids=[], parent=[];
for(let i=0;i<p.count;i++) {
  const key=[p.getX(i),p.getY(i),p.getZ(i)].map(v=>Math.round(v*1e6)).join(',');
  if(!keys.has(key)) {keys.set(key,parent.length);parent.push(parent.length);}
  ids.push(keys.get(key));
}
const find=i=>parent[i]===i ? i : (parent[i]=find(parent[i]));
const join=(a,b)=>{parent[find(a)]=find(b);};
for(let i=0;i<(pi?.count ?? p.count);i+=3) {
  const [a,b,c]=[0,1,2].map(j=>ids[pi ? pi.getX(i+j) : i+j]);join(a,b);join(b,c);
}
const pendantCount=new Set(parent.map((_,i)=>find(i))).size;
assert.equal(pendantCount,24);
const dropBounds=new Map();
for(let i=0;i<p.count;i++) {
  const component=find(ids[i]);
  if(!dropBounds.has(component)) dropBounds.set(component,new Box3());
  dropBounds.get(component).expandByPoint(new Vector3().fromBufferAttribute(p,i).applyMatrix4(pendant.matrixWorld));
}
const dropSizes=[...dropBounds.values()].map(b=>b.getSize(new Vector3()));
const pendantDimensions={
  height_range_m:[Math.min(...dropSizes.map(s=>s.y)),Math.max(...dropSizes.map(s=>s.y))],
  max_horizontal_span_m:Math.max(...dropSizes.flatMap(s=>[s.x,s.z]))
};
const report={result:'PASS',id:'atrium-chandelier',glb_bytes:bytes.length,triangles,vertices,
  stored_meshes:json.meshes.length,mesh_primitives:parts.length,opaque_draw_calls_per_pass:parts.length,
  materials:json.materials.length,images:0,animations:0,dimensions,
  bounds:{min:bounds.min.toArray(),max:bounds.max.toArray()},minimum_triangle_area_m2:minimumArea,
  concentric_light_tiers:tiers,measured_led_tier_vertex_counts:tierCounts,pendant_components:pendantCount,
  pendant_dimensions:pendantDimensions,
  sha256:createHash('sha256').update(bytes).digest('hex'),
  validation:{errors:validation.issues.numErrors,warnings:validation.issues.numWarnings,version:validator.version()},
  budget:{triangles_exclusive:20000,bytes_exclusive:1572864,materials_max:3,mesh_primitives:3},parts};
fs.writeFileSync(new URL('reports/assets.json',import.meta.url),JSON.stringify(report,null,2)+'\n');
console.log(JSON.stringify(report,null,2));

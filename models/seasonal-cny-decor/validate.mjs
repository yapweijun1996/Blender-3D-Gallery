import assert from 'node:assert/strict';
import fs from 'node:fs';
import { fileURLToPath } from 'node:url';
import { createHash } from 'node:crypto';
import { Box3, Vector3 } from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import validator from 'gltf-validator';

const dir=fileURLToPath(new URL('.',import.meta.url));
const spec=JSON.parse(fs.readFileSync(dir+'backlog.json'));
const bytes=fs.readFileSync(dir+'exports/optimized.glb');
const json=JSON.parse(bytes.subarray(20,20+bytes.readUInt32LE(12)));
const validation=await validator.validateBytes(new Uint8Array(bytes),{uri:'optimized.glb',maxIssues:200});
fs.writeFileSync(dir+'reports/khronos.json',JSON.stringify(validation,null,2)+'\n');
assert.equal(validation.issues.numErrors,0);
assert.equal(validation.issues.numWarnings,0);
assert.ok(json.buffers.every(b=>!b.uri));
assert.ok(!json.images?.length && !json.textures?.length && !json.cameras?.length && !json.extensions?.KHR_lights_punctual);
assert.equal(json.materials.length,3);
assert.ok(json.materials.every(m=>m.alphaMode===undefined || m.alphaMode==='OPAQUE'));
const gltf=await new GLTFLoader().parseAsync(bytes.buffer.slice(bytes.byteOffset,bytes.byteOffset+bytes.byteLength),'');
gltf.scene.updateMatrixWorld(true);
assert.equal(gltf.animations.length,0);
const root=gltf.scene.getObjectByName(spec.root);
assert.ok(root);
assert.deepEqual(root.position.toArray(),[0,0,0]);
assert.equal(root.userData.units,'metres');
const bounds=new Box3().setFromObject(root,true);
assert.ok(Math.abs(bounds.min.y)<1e-6,'floor datum');
assert.ok(Math.abs(bounds.getCenter(new Vector3()).x)<1e-6,'floor centre X');
assert.ok(Math.abs(bounds.getCenter(new Vector3()).z)<1e-6,'floor centre Z');
let triangles=0,vertices=0,primitives=0,degenerateTriangles=0;
const a=new Vector3(),b=new Vector3(),c=new Vector3();
root.traverse(o=>{
  if(!o.isMesh)return;
  const p=o.geometry.attributes.position,n=o.geometry.attributes.normal,index=o.geometry.index;
  assert.ok(n);
  assert.ok([...p.array,...n.array].every(Number.isFinite));
  for(let i=0;i<n.count;i++)assert.ok(Math.abs(new Vector3().fromBufferAttribute(n,i).length()-1)<1e-4,'unit normals');
  const count=index?.count??p.count;
  vertices+=p.count;
  triangles+=count/3;
  primitives++;
  for(let i=0;i<count;i+=3){
    a.fromBufferAttribute(p,index?index.getX(i):i);
    b.fromBufferAttribute(p,index?index.getX(i+1):i+1);
    c.fromBufferAttribute(p,index?index.getX(i+2):i+2);
    if(b.sub(a).cross(c.sub(a)).lengthSq()<1e-20)degenerateTriangles++;
  }
});
assert.equal(degenerateTriangles,0);
assert.ok(triangles<=spec.budget.triangles);
assert.ok(bytes.length<=spec.budget.bytes);
assert.ok(primitives<=spec.budget.mesh_primitives);
const parts={};
for(const name of ['LANTERN_01','LANTERN_02','BANNER_01','BANNER_02','PLANT_Red','PLANT_Green','PLANT_Gold','ENVELOPE_STAND']){
  const object=root.getObjectByName(name);
  assert.ok(object,name);
  const box=new Box3().setFromObject(object,true);
  parts[name]={min:box.min.toArray(),max:box.max.toArray(),dimensions:box.getSize(new Vector3()).toArray()};
}
for(const name of ['LANTERN_01','LANTERN_02']){
  assert.ok(parts[name].min[1]>1.1,'hanging lantern clearance');
  assert.ok(Math.abs(parts[name].dimensions[0]-.5)<.012,'half metre lantern width');
}
for(const name of ['BANNER_01','BANNER_02'])assert.ok(parts[name].min[1]>1.05,'banner including lower roller clears one metre plant');
const plantBounds=new Box3();
for(const name of ['PLANT_Red','PLANT_Green','PLANT_Gold'])plantBounds.union(new Box3().setFromObject(root.getObjectByName(name),true));
assert.ok(Math.abs(plantBounds.max.y-plantBounds.min.y-1)<1e-6,'one metre plant including pot');
assert.ok(Math.abs(parts.ENVELOPE_STAND.min[1])<1e-6,'stand floor support');
const report={result:'PASS',id:spec.slug,exporter:json.asset.generator,
  glb_bytes:bytes.length,triangles,vertices,mesh_objects:json.meshes.length,mesh_primitives:primitives,
  materials:json.materials.length,textures:json.textures?.length??0,animations:gltf.animations.length,
  degenerate_triangles:degenerateTriangles,dimensions_metres:bounds.getSize(new Vector3()).toArray(),
  bounds:{min:bounds.min.toArray(),max:bounds.max.toArray()},plant_height_metres:plantBounds.max.y-plantBounds.min.y,
  sha256:createHash('sha256').update(bytes).digest('hex'),budget:spec.budget,
  validation:{errors:validation.issues.numErrors,warnings:validation.issues.numWarnings},parts};
fs.writeFileSync(dir+'reports/assets.json',JSON.stringify(report,null,2)+'\n');
console.log(JSON.stringify(report,null,2));

import assert from 'node:assert/strict';
import fs from 'node:fs';
import { fileURLToPath } from 'node:url';
import { createHash } from 'node:crypto';
import { Box3, Vector3 } from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import validator from 'gltf-validator';

const dir = fileURLToPath(new URL('.', import.meta.url));
const spec = JSON.parse(fs.readFileSync(dir+'backlog.json'));
const bytes = fs.readFileSync(dir+'exports/optimized.glb');
const json = JSON.parse(bytes.subarray(20,20+bytes.readUInt32LE(12)));
const validation = await validator.validateBytes(new Uint8Array(bytes), { uri:'optimized.glb', maxIssues:200 });
fs.writeFileSync(dir+'reports/khronos.json', JSON.stringify(validation,null,2)+'\n');
assert.equal(validation.issues.numErrors,0);
assert.equal(validation.issues.numWarnings,0);
assert.ok(!json.images?.length && !json.textures?.length && !json.cameras?.length && !json.extensions?.KHR_lights_punctual);
assert.ok(json.buffers.every(b=>!b.uri));
assert.equal(json.materials.length,3);
assert.ok(json.materials.every(m=>m.alphaMode === undefined || m.alphaMode === 'OPAQUE'));
const gltf = await new GLTFLoader().parseAsync(bytes.buffer.slice(bytes.byteOffset,bytes.byteOffset+bytes.byteLength),'');
gltf.scene.updateMatrixWorld(true);
assert.equal(gltf.animations.length,0);
const root = gltf.scene.getObjectByName(spec.root);
assert.ok(root);
assert.deepEqual(root.position.toArray(),[0,0,0]);
assert.equal(root.userData.units,'metres');
const bounds = new Box3().setFromObject(root,true);
assert.ok(Math.abs(bounds.min.y)<1e-6,'floor datum');
assert.ok(Math.abs(bounds.getCenter(new Vector3()).x)<1e-6,'floor centre X');
assert.ok(Math.abs(bounds.getCenter(new Vector3()).z)<1e-6,'floor centre Z');
assert.ok(Math.abs(bounds.max.y-2.5)<1e-6,'tree including star is 2.5 m');
let triangles=0,vertices=0,primitives=0,degenerateTriangles=0;
const parts = {};
const treeBounds = new Box3();
const a=new Vector3(),b=new Vector3(),c=new Vector3();
root.traverse(o=>{
  if(!o.isMesh)return;
  const geo=o.geometry,position=geo.attributes.position,index=geo.index;
  assert.ok(geo.attributes.normal);
  assert.ok([...position.array,...geo.attributes.normal.array].every(Number.isFinite));
  vertices+=position.count;
  const count=index?.count??position.count;
  triangles+=count/3;
  primitives++;
  for(let i=0;i<count;i+=3){
    a.fromBufferAttribute(position,index?index.getX(i):i);
    b.fromBufferAttribute(position,index?index.getX(i+1):i+1);
    c.fromBufferAttribute(position,index?index.getX(i+2):i+2);
    if(b.sub(a).cross(c.sub(a)).lengthSq()<1e-20)degenerateTriangles++;
  }
  const box = new Box3().setFromObject(o,true);
  if(o.name.startsWith('TREE_'))treeBounds.union(box);
  parts[o.name]={min:box.min.toArray(),max:box.max.toArray(),triangles:count/3};
});
assert.equal(degenerateTriangles,0);
assert.ok(triangles<=spec.budget.triangles);
assert.ok(bytes.length<=spec.budget.bytes);
assert.equal(primitives,8);
for(const name of ['TREE_Pine','TREE_Cranberry','TREE_Champagne','GIFTS_Pine','GIFTS_Cranberry','GIFTS_Champagne','SNOWFLAKE_01_Champagne','SNOWFLAKE_02_Champagne'])assert.ok(parts[name],name);
assert.ok(Math.abs(treeBounds.max.y-treeBounds.min.y-2.5)<1e-6);
for(const name of ['SNOWFLAKE_01_Champagne','SNOWFLAKE_02_Champagne'])assert.ok(parts[name].min[1]>1.4,'suspended ornament');
const report={result:'PASS',id:spec.slug,exporter:json.asset.generator,glb_bytes:bytes.length,
  triangles,vertices,mesh_primitives:primitives,materials:json.materials.length,animations:gltf.animations.length,
  textures:json.textures?.length??0,degenerate_triangles:degenerateTriangles,
  dimensions_metres:bounds.getSize(new Vector3()).toArray(),bounds:{min:bounds.min.toArray(),max:bounds.max.toArray()},
  tree_height_metres:treeBounds.max.y-treeBounds.min.y,
  sha256:createHash('sha256').update(bytes).digest('hex'),budget:spec.budget,
  validation:{errors:validation.issues.numErrors,warnings:validation.issues.numWarnings,infos:validation.issues.numInfos},parts};
fs.writeFileSync(dir+'reports/assets.json',JSON.stringify(report,null,2)+'\n');
console.log(JSON.stringify(report,null,2));

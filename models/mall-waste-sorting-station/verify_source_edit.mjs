import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
import { fileURLToPath } from 'node:url';
import { createHash } from 'node:crypto';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import validator from 'gltf-validator';
const here=path.dirname(fileURLToPath(import.meta.url));
assert.ok(process.argv[2], 'Pass the isolated test_source_edit.py output directory');
const paths=[path.join(here,'exports/mall-waste-sorting-station.glb'),path.resolve(process.argv[2],'exports/mall-waste-sorting-station.glb')];
const groups=['StationFrame','RecycleCompartment','FoodCompartment','GeneralCompartment','RecycleLid','FoodLid','GeneralLid'];
const results=[];
for(const file of paths){
  const bytes=fs.readFileSync(file);
  const validation=await validator.validateBytes(new Uint8Array(bytes));
  assert.equal(validation.issues.numErrors,0);assert.equal(validation.issues.numWarnings,0);
  const gltf=await new GLTFLoader().parseAsync(bytes.buffer.slice(bytes.byteOffset,bytes.byteOffset+bytes.byteLength),'');gltf.scene.updateMatrixWorld(true);
  const hashes={};
  for(const group of groups){
    const hash=createHash('sha256');gltf.scene.getObjectByName(group).traverse(o=>{
      if(!o.isMesh)return;
      hash.update(JSON.stringify(o.matrixWorld.elements));
      for(const [name,attr] of Object.entries(o.geometry.attributes)){hash.update(name);hash.update(Buffer.from(attr.array.buffer,attr.array.byteOffset,attr.array.byteLength));}
      if(o.geometry.index)hash.update(Buffer.from(o.geometry.index.array.buffer,o.geometry.index.array.byteOffset,o.geometry.index.array.byteLength));
      const m=o.material;hash.update(JSON.stringify({color:m.color.toArray(),metalness:m.metalness,roughness:m.roughness}));
    });hashes[group]=hash.digest('hex');
  }
  results.push({asset:results.length?'isolated edited source':'shipped asset',sha256:createHash('sha256').update(bytes).digest('hex'),groupHashes:hashes,validation:{errors:0,warnings:0}});
}
for(const group of groups) if(group==='RecycleLid')assert.notEqual(results[0].groupHashes[group],results[1].groupHashes[group]);else assert.equal(results[0].groupHashes[group],results[1].groupHashes[group],group);
const original=JSON.parse(fs.readFileSync(path.join(here,'reports/assets.json')));
assert.equal(results[0].sha256,original.sha256);
const report={status:'PASS',edit:'RECYCLE -> PLASTIC in an isolated copy of the saved Blender source',exportMode:'generate.py -- --export-source',changedGroups:['RecycleLid'],unchangedGroups:groups.filter(n=>n!=='RecycleLid'),originalAssetUnchanged:true,results};
fs.writeFileSync(path.join(here,'reports/source-edit.json'),JSON.stringify(report,null,2)+'\n');
console.log(JSON.stringify(report,null,2));

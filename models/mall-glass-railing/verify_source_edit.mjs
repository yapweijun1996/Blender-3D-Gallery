import assert from 'node:assert/strict';import fs from 'node:fs';import path from 'node:path';import {fileURLToPath} from 'node:url';import {createHash} from 'node:crypto';import validator from 'gltf-validator';
const root=path.dirname(fileURLToPath(import.meta.url)),out=process.argv[2];assert.ok(out);
const comparisons=[];
for(const suffix of ['post','1m','2m']){
  const id='mall-glass-railing-'+suffix;
  const a=fs.readFileSync(path.join(root,'exports',id+'.glb')),b=fs.readFileSync(path.join(out,'exports',id+'.glb'));
  const j=x=>JSON.parse(x.subarray(20,20+x.readUInt32LE(12))),ja=j(a),jb=j(b);
  const val=await validator.validateBytes(new Uint8Array(b));assert.equal(val.issues.numErrors,0);assert.equal(val.issues.numWarnings,0);
  assert.deepEqual(ja.meshes,jb.meshes);assert.deepEqual(ja.nodes,jb.nodes);
  assert.deepEqual(a.subarray(20+a.readUInt32LE(12)),b.subarray(20+b.readUInt32LE(12)));
  if(suffix==='1m'){
    const ga=ja.materials.find(m=>m.name.startsWith('GLASS ')),gb=jb.materials.find(m=>m.name.startsWith('GLASS '));
    assert.ok(Math.abs(ga.pbrMetallicRoughness.baseColorFactor[3]-.28)<1e-6);
    assert.ok(Math.abs(gb.pbrMetallicRoughness.baseColorFactor[3]-.44)<1e-6);
    gb.pbrMetallicRoughness.baseColorFactor[3]=ga.pbrMetallicRoughness.baseColorFactor[3];
  }
  assert.deepEqual(ja,jb);
  comparisons.push({id,geometryAndNodesUnchanged:true,onlyChange:suffix==='1m'?'glass alpha 0.28 -> 0.44':'none',originalSha256:createHash('sha256').update(a).digest('hex'),editedSha256:createHash('sha256').update(b).digest('hex')});
}
fs.writeFileSync(path.join(root,'reports/source-edit.json'),JSON.stringify({status:'PASS',method:'Edited isolated saved .blend, then generate.py -- --export-source',comparisons},null,2)+'\n');
console.log('PASS isolated saved-source material edit and export');

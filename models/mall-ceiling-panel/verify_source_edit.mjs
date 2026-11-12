import assert from 'node:assert/strict';import fs from 'node:fs';import {fileURLToPath} from 'node:url';import {createHash} from 'node:crypto';import {Box3} from 'three';import validator from 'gltf-validator';import {readGlb,near} from './glb.mjs';
const root=fileURLToPath(new URL('.',import.meta.url)),out=process.argv[2];assert.ok(out);
const a=await readGlb(root+'exports/mall-ceiling-panel-module.glb'),b=await readGlb(out+'/exports/mall-ceiling-panel-module.glb');
const val=await validator.validateBytes(new Uint8Array(b.bytes));assert.equal(val.issues.numErrors,0);assert.equal(val.issues.numWarnings,0);
const sha=v=>createHash('sha256').update(v).digest('hex');
assert.equal(JSON.parse(fs.readFileSync(root+'reports/sources.json')).source_sha256,sha(fs.readFileSync(root+'sources/mall-ceiling-panel-module.blend')));
for(const o of a.scene.getObjectByName('ASSET_MallCeilingPanel').children){
 const other=b.scene.getObjectByName(o.name);assert.ok(other);
 if(o.name.startsWith('CONNECTOR_'))continue;
 const ba=new Box3().setFromObject(o),bb=new Box3().setFromObject(other);
 near(bb.min.y,ba.min.y-(o.name==='PANEL_1'?.002:0));near(bb.max.y,ba.max.y);
 for(const dim of ['x','z']){near(ba.min[dim],bb.min[dim]);near(ba.max[dim],bb.max[dim]);}
}
const mat=j=>j.materials.find(m=>m.name.startsWith('Mineral fibre'));near(mat(a.json).pbrMetallicRoughness.roughnessFactor,.85);near(mat(b.json).pbrMetallicRoughness.roughnessFactor,.65);
function imageHash(g){const v=g.json.bufferViews[g.json.images[0].bufferView],offset=20+g.bytes.readUInt32LE(12)+8;return sha(g.bytes.subarray(offset+(v.byteOffset||0),offset+(v.byteOffset||0)+v.byteLength));}
assert.equal(imageHash(a),imageHash(b));
const report={status:'PASS',method:'Reopened shipped .blend, isolated copy, PANEL_1 underside vertices lowered 2 mm, shared underside roughness edited 0.85 to 0.65, saved and re-exported with --export-source',otherMeshBoundsUnchanged:true,originalTextureUnchanged:true,shippedSourceUnchanged:true,originalSha256:sha(a.bytes),editedSha256:sha(b.bytes),editedValidation:{errors:0,warnings:0}};
fs.writeFileSync(root+'reports/source-edit.json',JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report));

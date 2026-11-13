import assert from 'node:assert/strict';import fs from 'node:fs';import {fileURLToPath} from 'node:url';import {createHash} from 'node:crypto';import {Box3,Vector3} from 'three';import validator from 'gltf-validator';import {readGlb,near} from './glb.mjs';
const root=fileURLToPath(new URL('.',import.meta.url)),out=process.argv[2];assert.ok(out);
const a=await readGlb(root+'exports/mall-floor-tile-module.glb'),b=await readGlb(out+'/exports/mall-floor-tile-module.glb');
const val=await validator.validateBytes(new Uint8Array(b.bytes));assert.equal(val.issues.numErrors,0);assert.equal(val.issues.numWarnings,0);
const originalSource=JSON.parse(fs.readFileSync(root+'reports/sources.json')).source_sha256;assert.equal(originalSource,createHash('sha256').update(fs.readFileSync(root+'sources/mall-floor-tile-module.blend')).digest('hex'));
for(const name of ['MODULE_GroutBed',...Array.from({length:4},(_,i)=>'MODULE_Tile_'+(i+1))]){
 const ba=new Box3().setFromObject(a.scene.getObjectByName(name)),bb=new Box3().setFromObject(b.scene.getObjectByName(name));
 near(ba.min.y,bb.min.y);near(bb.max.y,ba.max.y+(name==='MODULE_Tile_1'?.004:0));
 for(const dim of ['x','z']){near(ba.min[dim],bb.min[dim]);near(ba.max[dim],bb.max[dim]);}
}
const mat=j=>j.materials.find(m=>m.name.startsWith('Honed ivory'));near(mat(a.json).pbrMetallicRoughness.roughnessFactor,.32);near(mat(b.json).pbrMetallicRoughness.roughnessFactor,.48);
function imageHash(g){const v=g.json.bufferViews[g.json.images[0].bufferView],offset=20+g.bytes.readUInt32LE(12)+8;return createHash('sha256').update(g.bytes.subarray(offset+(v.byteOffset||0),offset+(v.byteOffset||0)+v.byteLength)).digest('hex');}
assert.equal(imageHash(a),imageHash(b));
const report={status:'PASS',method:'Isolated saved .blend reopened, first slab top vertices raised 4 mm, shared finish roughness edited 0.32 to 0.48, source saved and re-exported with --export-source',otherSlabAndBedBoundsUnchanged:true,originalTextureUnchanged:true,shippedSourceUnchanged:true,originalSha256:createHash('sha256').update(a.bytes).digest('hex'),editedSha256:createHash('sha256').update(b.bytes).digest('hex'),editedValidation:{errors:0,warnings:0}};
fs.writeFileSync(root+'reports/source-edit.json',JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report));

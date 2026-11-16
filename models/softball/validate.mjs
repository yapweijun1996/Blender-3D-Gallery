import assert from 'node:assert/strict';
import fs from 'node:fs';
import { createHash } from 'node:crypto';
import { fileURLToPath } from 'node:url';
import { Box3, Vector3 } from 'three';
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
const jsonLength = bytes.readUInt32LE(12);
const bin = bytes.subarray(28 + jsonLength, 28 + jsonLength + bytes.readUInt32LE(20 + jsonLength));
const geometryJson = structuredClone(json);
delete geometryJson.images;
delete geometryJson.textures;
delete geometryJson.samplers;
for (const material of geometryJson.materials) delete material.normalTexture;
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
assert.equal(gltf.animations.length, 0);


assert.equal(json.images.length,1);assert.equal(json.textures.length,1);
const imageInfo=validation.info.resources.find(r=>r.image)?.image;
assert.equal(imageInfo.width,1024);assert.equal(imageInfo.height,512);
assert.ok(json.images.every(i=>i.bufferView!==undefined && !i.uri && i.mimeType==='image/jpeg'));
assert.ok(!json.cameras?.length && !json.extensions?.KHR_lights_punctual);
assert.ok(json.buffers.every(b=>!b.uri));
assert.ok(json.materials.every(m=>m.pbrMetallicRoughness.metallicFactor===0));
const cfg=JSON.parse(fs.readFileSync(dir+'config.json'));
let triangles=0,vertices=0,primitives=0;const parts={};const positionsByMaterial={};
function components(g) {
 const p=g.attributes.position, idx=g.index;
 const ids=Array.from({length:p.count},(_,i)=>[p.getX(i),p.getY(i),p.getZ(i)].map(v=>Math.round(v*1e7)).join(','));
 const parent=new Map(ids.map(i=>[i,i]));
 const find=a=>{while(parent.get(a)!==a){parent.set(a,parent.get(parent.get(a)));a=parent.get(a);}return a;};
 for(let i=0;i<idx.count;i+=3){const a=ids[idx.getX(i)];for(let k=1;k<3;k++)parent.set(find(ids[idx.getX(i+k)]),find(a));}
 return new Set(ids.map(find)).size;
}
gltf.scene.traverse(o=>{
 if(!o.isMesh)return;
 const g=o.geometry,p=g.attributes.position,idx=g.index;
 for(const a of Object.values(g.attributes)) assert.ok(Array.from(a.array).every(Number.isFinite),'finite attributes');
 assert.ok(g.attributes.normal && g.attributes.uv);
 for(let i=0;i<idx.count;i+=3){
  const v=[0,1,2].map(k=>new Vector3().fromBufferAttribute(p,idx.getX(i+k)));
  assert.ok(v[1].sub(v[0]).cross(v[2].sub(v[0])).lengthSq()>1e-23,'nondegenerate triangles');
 }
 positionsByMaterial[o.material.name]=Array.from({length:p.count},(_,i)=>new Vector3().fromBufferAttribute(p,i).applyMatrix4(o.matrixWorld));
 parts[o.material.name]={components:components(g),triangles:idx.count/3,vertices:p.count};
 triangles+=idx.count/3;vertices+=p.count;primitives++;
});
assert.ok(triangles<=spec.budget.triangles && bytes.length<=spec.budget.bytes);
assert.ok(triangles<=40000 && bytes.length<=1572864,'absolute task limits');
assert.ok(primitives<=spec.budget.mesh_primitives && json.materials.length<=spec.budget.materials);
const bounds=new Box3().setFromObject(gltf.scene,true), dimensions=bounds.getSize(new Vector3()).toArray();
assert.ok(Math.abs(bounds.min.y)<2e-6,'floor contact');
assert.ok(Math.abs(bounds.min.x+bounds.max.x)<.000002 && Math.abs(bounds.min.z+bounds.max.z)<.000002,'centred');
const tolerance=spec.slug==='table-tennis-ball'?.00006:spec.slug==='tennis-ball'?.00010:.0012;
for(const d of dimensions) assert.ok(Math.abs(d-cfg.diameter)<tolerance,'diameter within justified sampling/thread tolerance');
assert.equal(root.userData.panels,cfg.panels);assert.equal(root.userData.stitch_pairs,cfg.stitch_pairs);
assert.equal(json.meshes.length,1,'one combined exported mesh');
assert.equal(primitives,json.materials.length,'one primitive per material');
if(['tennis-ball','baseball','softball'].includes(spec.slug)) {
 assert.equal(parts[spec.slug==='tennis-ball'?'Felt':'Cover'].components,2,'two separate cover halves');
 assert.equal(parts[spec.slug==='tennis-ball'?'Rubber_seam':'Seam']?.components ?? parts['Rubber seam']?.components,1,'continuous seam band');
 assert.equal(source.panels,2);
 if(cfg.stitch_pairs) assert.equal(parts.Stitches.components,cfg.stitch_pairs*2,'two strands per V stitch pair');
}
if(spec.slug==='cricket-ball') {
 assert.equal(source.stitch_rows,6);assert.equal(parts.Stitches.components,6*72,'six rows of 72 separate stitches');
 assert.equal(parts.Seam.components,3,'primary welt and two quarter seams');
 assert.equal(parts.Cover.components,1);
}
if(spec.slug==='table-tennis-ball') {
 assert.equal(parts.Cover.components,1);
 assert.ok(dimensions[0]<.04 && dimensions[0]>.0399,'faint equatorial groove');
}
// Independently enforce the batch's exact feature counts, not only config consistency.
const counts={'tennis-ball':0,baseball:108,softball:88,'cricket-ball':72,'table-tennis-ball':0};
assert.equal(cfg.stitch_pairs,counts[spec.slug]);
assert.equal(root.userData.up_axis,'Blender +Z / glTF +Y');
const adjustment=root.userData.horizontal_adjustment_m;
const centre=new Vector3(adjustment[0],cfg.diameter/2+root.userData.floor_adjustment_m,-adjustment[1]);
const skin=positionsByMaterial[spec.slug==='tennis-ball'?'Felt':'Cover'];
assert.ok(skin.every(v=>Math.abs(v.distanceTo(centre)-cfg.diameter/2)<.00006),'skin on nominal spherical surface within 60 micrometres, including shallow join');
if(spec.slug==='tennis-ball') {
 const seam=positionsByMaterial['Rubber seam'];const radii=seam.map(v=>v.distanceTo(centre));
 assert.ok(Math.min(...radii)<cfg.diameter/2-.00020,'rubber band genuinely recessed');
 assert.ok(Math.max(...radii)<=cfg.diameter/2+1e-7);
 assert.ok(json.materials.find(m=>m.name==='Felt').normalTexture,'felt grain survives export');
 assert.ok(json.materials.find(m=>m.name==='Felt').pbrMetallicRoughness.roughnessFactor>.9);
}
if(spec.slug==='cricket-ball') {
 const axis=new Vector3(0,Math.cos(.72),Math.sin(.72));
 const rowVertices=Array(6).fill(0);
 for(const v of positionsByMaterial.Stitches){
  const lat=Math.asin(v.clone().sub(centre).normalize().dot(axis));
  const row=Math.round(lat/.034+2.5);
  assert.ok(row>=0 && row<6 && Math.abs(lat-(row-2.5)*.034)<.012,'thread in one of six physical rows');
  rowVertices[row]++;
 }
 assert.ok(rowVertices.every(n=>n>0),'all six rows populated');
}
const report={result:'PASS',id:spec.slug,glb_bytes:bytes.length,triangles,vertices,meshes:json.meshes.length,primitives,
 materials:json.materials.length,textures:json.textures.length,animations:gltf.animations.length,
 dimensions_m:dimensions,bounds_m:{min:bounds.min.toArray(),max:bounds.max.toArray()},
 diameter_m:cfg.diameter,circumference_m:cfg.diameter*Math.PI,panels:cfg.panels,stitch_pairs:cfg.stitch_pairs,
 stitch_rows:source.stitch_rows,parts,sha256:createHash('sha256').update(bytes).digest('hex'),budget:spec.budget,
 validation:{errors:validation.issues.numErrors,warnings:validation.issues.numWarnings,infos:validation.issues.numInfos}};
fs.writeFileSync(dir+'reports/assets.json',JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report,null,2));

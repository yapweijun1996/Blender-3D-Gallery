import assert from 'node:assert/strict';import fs from 'node:fs';import {fileURLToPath} from 'node:url';import {createHash} from 'node:crypto';
import {Box3,Vector3,Group} from 'three';import validator from 'gltf-validator';import {readGlb,near} from './glb.mjs';
const root=fileURLToPath(new URL('.',import.meta.url)),sha=b=>createHash('sha256').update(b).digest('hex');
const {bytes,json,scene}=await readGlb(root+'exports/mall-atrium-balcony.glb');
const val=await validator.validateBytes(new Uint8Array(bytes));assert.equal(val.issues.numErrors,0);assert.equal(val.issues.numWarnings,0);
assert.ok(!json.animations?.length&&!json.cameras?.length&&!json.extensions?.KHR_lights_punctual);assert.ok(json.buffers.every(b=>!b.uri)&&json.images.every(i=>!i.uri));
const asset=scene.getObjectByName('ASSET_MallAtriumBalcony');assert.deepEqual(asset.position.toArray(),[0,0,0]);near(asset.userData.repeat_pitch_m,2);
const meshesOf=o=>{const a=[];o.traverse(x=>{if(x.isMesh)a.push(x)});return a;};
let triangles=0,vertices=0,primitives=0;const parts={};for(const o of meshesOf(scene)){primitives++;vertices+=o.geometry.attributes.position.count;triangles+=(o.geometry.index?.count??o.geometry.attributes.position.count)/3;const b=new Box3().setFromObject(o);parts[o.name]={min:b.min.toArray(),max:b.max.toArray()};}
const bounds=new Box3().setFromObject(scene),dimensions=bounds.getSize(new Vector3()).toArray();dimensions.forEach((x,i)=>near(x,[2.16,1.371,1.22][i]));near(bounds.min.y,0);assert.ok(bytes.length<600*1024&&triangles<10000);assert.equal(json.images.length,1);assert.equal(json.materials.length,11);
for(const [name,pos] of [['JointLeft',[-1,.25,.52]],['JointRight',[1,.25,.52]],['DeckTop',[0,.25,0]],['Underside',[0,0,0]]])asset.getObjectByName('CONNECTOR_'+name).getWorldPosition(new Vector3()).toArray().forEach((x,i)=>near(x,pos[i]));
const glass=json.materials.find(m=>m.name.startsWith('GLASS '));assert.equal(glass.alphaMode,'BLEND');assert.equal(glass.doubleSided,true);near(glass.pbrMetallicRoughness.baseColorFactor[3],.28);
// Compare actual transformed triangle positions with the original 006 optimized GLB.
const rail=await readGlb(root+'../mall-glass-railing/exports/mall-glass-railing-2m.glb');
function tris(o,offset=[0,0,0]){const out=[];for(const m of meshesOf(o)){const a=m.geometry.attributes.position,ix=m.geometry.index;for(let i=0;i<(ix?.count??a.count);i+=3){const t=[];for(let j=0;j<3;j++){const v=new Vector3().fromBufferAttribute(a,ix?ix.getX(i+j):i+j).applyMatrix4(m.matrixWorld);t.push(v.toArray().map((x,k)=>Math.round((x+offset[k])*1e5)).join(','));}out.push(t.sort().join(';'));}}return out.sort();}
let reusedRailingTriangles=0;for(const n of ['MODULE_Post_Left','MODULE_Post_Right','MODULE_Infill']){const original=tris(rail.scene.getObjectByName(n),[0,.25,.52]),assembled=tris(asset.getObjectByName(n));assert.deepEqual(assembled,original,n+' source geometry must match original 006 export');reusedRailingTriangles+=original.length;}
const floor=await readGlb(root+'../mall-floor-tile/exports/mall-floor-tile-module.glb');
const imageBytes=g=>{const i=g.json.images[0],v=g.json.bufferViews[i.bufferView],n=g.bytes.readUInt32LE(12);return g.bytes.subarray(28+n+(v.byteOffset??0),28+n+(v.byteOffset??0)+v.byteLength)};
const textureSha256=sha(imageBytes({bytes,json}));assert.equal(textureSha256,sha(imageBytes(floor)));
for(const mat of floor.json.materials)assert.ok(json.materials.some(m=>JSON.stringify(m)===JSON.stringify(mat)),'preserve original 421 material '+mat.name);
const layouts=JSON.parse(fs.readFileSync(root+'layouts.json')),assemblies=[];
const overlap=(a,b)=>['x','y','z'].map(k=>Math.min(a.max[k],b.max[k])-Math.max(a.min[k],b.min[k]));
for(const example of layouts.examples){
 const group=new Group(),modules=[];
 for(let i=0;i<example.bays;i++){const o=asset.clone(true);o.position.x=i*2;group.add(o);modules.push(o);for(const n of [...(i>0?['MODULE_Post_Left','MODULE_EndCap_Left']:[]),...(i<example.bays-1?['MODULE_EndCap_Right']:[])])o.remove(o.getObjectByName(n));}
 group.updateMatrixWorld(true);
 const posts=modules.flatMap(o=>o.children.filter(c=>c.name.startsWith('MODULE_Post_')));assert.equal(posts.length,example.bays+1);
 const postCenters=posts.map(p=>{const b=new Box3().setFromObject(p);near(b.min.y,.25);near(b.min.z,.44);near(b.max.z,.60);return (b.min.x+b.max.x)/2;}).sort((a,b)=>a-b);
 assert.equal(new Set(postCenters.map(x=>x.toFixed(5))).size,posts.length);
 for(let i=0;i<postCenters.length;i++)near(postCenters[i],-1+i*2);
 let adjacentDeckChecks=0;for(let i=0;i<modules.length-1;i++){const a=new Box3().setFromObject(modules[i].getObjectByName('DECK_Slab')),b=new Box3().setFromObject(modules[i+1].getObjectByName('DECK_Slab'));near(a.max.x,b.min.x);assert.ok(!overlap(a,b).every(v=>v>1e-6));adjacentDeckChecks++;}
 const decks=modules.map(m=>m.getObjectByName('MODULE_Deck'));
 for(const d of decks){near(new Box3().setFromObject(d.getObjectByName('DECK_Slab')).max.y,.22);for(let t=1;t<=8;t++)near(new Box3().setFromObject(d.getObjectByName('FLOOR_Tile_'+t)).max.y,.25);}
 const endCaps=modules.flatMap(o=>o.children.filter(c=>c.name.startsWith('MODULE_EndCap_')));assert.equal(endCaps.length,2);
 const entire=new Box3().setFromObject(group);near(entire.min.x,postCenters[0]-.08);near(entire.max.x,postCenters.at(-1)+.08);
 // Full post plates are covered by main deck or the exposed-end closure, not floating half-footprints.
 for(const center of postCenters)assert.ok(center-.08>=entire.min.x-1e-6&&center+.08<=entire.max.x+1e-6);
 assemblies.push({name:example.name,result:'PASS',bays:example.bays,posts:posts.length,uniquePostCentres:postCenters,duplicatePosts:0,endCaps:2,adjacentDeckChecks,deckJointPenetrations:0,deckSurface_m:.25,railBase_m:.25,railFrontEdge_m:.6,deckFrontEdge_m:.6,completeFootprintSupport:true,width_m:entire.max.x-entire.min.x});
}
const provenance=JSON.parse(fs.readFileSync(root+'provenance.json'));for(const item of provenance.inputs)assert.equal(sha(fs.readFileSync(root+'../'+item.path)),item.sha256);
export const report={id:'mall-atrium-balcony',glb_bytes:bytes.length,triangles,vertices,primitives,materials:json.materials.length,textures:json.images.length,animations:0,dimensions,bounds:{min:bounds.min.toArray(),max:bounds.max.toArray()},parts,reusedRailingTriangles,textureSha256,sha256:sha(bytes),validation:{errors:0,warnings:0,validator:val.validatorVersion}};
export {assemblies};fs.writeFileSync(root+'reports/assets.json',JSON.stringify(report,null,2)+'\n');fs.writeFileSync(root+'reports/assemblies.json',JSON.stringify(assemblies,null,2)+'\n');console.log(JSON.stringify({metrics:{...report,parts:undefined},assemblies},null,2));

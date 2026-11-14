import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import assert from 'node:assert/strict';
import * as T from 'three';
import validator from 'gltf-validator';

const H=path.dirname(new URL(import.meta.url).pathname), file=path.join(H,'exports/demo-beverage-can.glb');
assert.ok(fs.existsSync(file),'host-generated GLB is required');
const bytes=fs.readFileSync(file), jsonLen=bytes.readUInt32LE(12), j=JSON.parse(bytes.subarray(20,20+jsonLen)), bin=bytes.subarray(28+jsonLen);
function acc(i){const a=j.accessors[i],v=j.bufferViews[a.bufferView],n={SCALAR:1,VEC2:2,VEC3:3,VEC4:4}[a.type],sz={5126:4,5125:4,5123:2,5121:1}[a.componentType],read={5126:'readFloatLE',5125:'readUInt32LE',5123:'readUInt16LE',5121:'readUInt8'}[a.componentType];return Array.from({length:a.count},(_,k)=>Array.from({length:n},(_,c)=>bin[read]((v.byteOffset||0)+(a.byteOffset||0)+k*(v.byteStride||n*sz)+c*sz)));}
const nodes=j.nodes.map(n=>{const o=new T.Object3D();o.name=n.name;o.position.fromArray(n.translation||[0,0,0]);o.quaternion.fromArray(n.rotation||[0,0,0,1]);o.scale.fromArray(n.scale||[1,1,1]);return o;}); j.nodes.forEach((n,i)=>(n.children||[]).forEach(c=>nodes[i].add(nodes[c])));
const byname=n=>nodes.find(o=>o.name===n), root=byname('ASSET_DemoBeverageCan'); assert(root); root.updateMatrixWorld(true);
['BODY_HollowShell','RIM_NeckedUpper','TOP_AperturePlate','TOP_InnerApertureWall','LABEL_OriginalCitrusBand','MOVABLE_Top','MOVABLE_Tab','MOVABLE_ScoreFlap'].forEach(n=>assert(byname(n),n));
assert.equal(byname('MOVABLE_Tab').parent,byname('MOVABLE_Top')); assert.equal(byname('MOVABLE_ScoreFlap').parent,byname('MOVABLE_Top')); assert(!byname('MOVABLE_PullRing'));
let triangles=0,primitives=0;for(const m of j.meshes)for(const p of m.primitives){primitives++;triangles+=(p.indices!==undefined?j.accessors[p.indices].count:j.accessors[p.attributes.POSITION].count)/3;}assert(triangles<=18000);assert(primitives<=18);assert(bytes.length<=1000000);
assert.equal(j.animations.length,2);assert.deepEqual(j.animations.map(a=>a.name).sort(),['Exploded','OpenClose']);
const meshFor=o=>{const node=j.nodes[nodes.indexOf(o)];assert(node?.mesh!==undefined,`Node has no mesh: ${o?.name}`);return j.meshes[node.mesh];};
const lm=meshFor(byname('LABEL_OriginalCitrusBand'));assert(lm.primitives.every(p=>p.attributes.TEXCOORD_0!==undefined));const uv=acc(lm.primitives[0].attributes.TEXCOORD_0);assert(Math.min(...uv.map(x=>x[0]))===0);assert(Math.max(...uv.map(x=>x[0]))===1);
const all=['BASE_ConcaveFoot','BODY_HollowShell','RIM_BaseBead','RIM_NeckedUpper','TOP_AperturePlate','TOP_InnerApertureWall','LABEL_OriginalCitrusBand'].flatMap(n=>{const o=byname(n),m=meshFor(o);return m.primitives.flatMap(p=>acc(p.attributes.POSITION).map(v=>new T.Vector3(...v).applyMatrix4(o.matrixWorld)));});const box=new T.Box3().setFromPoints(all),dims=box.getSize(new T.Vector3()).toArray();assert(dims[0]>.065&&dims[0]<.069,`width ${dims}`);assert(dims[1]>.113&&dims[1]<.13,`height ${dims}`);assert(dims[2]>.065&&dims[2]<.069,`depth ${dims}`);assert(box.min.y>=0&&box.max.y>.115,`bounds ${box.min.toArray()} ${box.max.toArray()}`);
const animationReport=[];for(const a of j.animations){const tracks=a.channels.map(c=>{const s=a.samplers[c.sampler],t=acc(s.input).flat(),v=acc(s.output);assert.equal(t[0],0);assert.equal(t.at(-1),3);assert(v[0].every((x,i)=>Math.abs(x-v.at(-1)[i])<1e-6));return{node:nodes[c.target.node].name,path:c.target.path,values:v,times:t};});assert(tracks.some(t=>['MOVABLE_Tab','MOVABLE_ScoreFlap','MOVABLE_Top'].includes(t.node)));animationReport.push({name:a.name,tracks});}
const opening=animationReport.find(a=>a.name==='OpenClose').tracks;
assert.deepEqual(opening.map(t=>t.node).sort(),['MOVABLE_ScoreFlap','MOVABLE_Tab']);
for(const [name,angle] of [['MOVABLE_ScoreFlap',.95],['MOVABLE_Tab',-1.05]]){
 const t=opening.find(t=>t.node===name);assert.equal(t.path,'rotation');const i=t.times.findIndex(v=>Math.abs(v-1.5)<1e-5);assert(i>=0);const q=t.values[i];assert(Math.abs(q[0]-Math.sin(angle/2))<1e-5);assert(Math.abs(q[3]-Math.cos(angle/2))<1e-5);
}
const explosion=animationReport.find(a=>a.name==='Exploded').tracks;assert.equal(explosion.length,1);assert.equal(explosion[0].node,'MOVABLE_Top');assert.equal(explosion[0].path,'translation');const middle=explosion[0].times.findIndex(v=>Math.abs(v-1.5)<1e-5);assert(Math.abs(explosion[0].values[middle][1]-explosion[0].values[0][1]-.07)<1e-5);
assert.equal(j.images.length,1);const iv=j.bufferViews[j.images[0].bufferView],png=bin.subarray(iv.byteOffset,iv.byteOffset+iv.byteLength);assert.equal(png.toString('ascii',1,4),'PNG');assert(png.readUInt32BE(16)<=2048&&png.readUInt32BE(20)<=1024);assert.equal(png.readUInt32BE(16),1024);assert.equal(png.readUInt32BE(20),512);
const validation=await validator.validateBytes(new Uint8Array(bytes),{uri:'demo-beverage-can.glb'});assert.equal(validation.issues.numErrors,0);const result={status:'PASS',sha256:crypto.createHash('sha256').update(bytes).digest('hex'),bytes:bytes.length,triangles,primitives,dimensions:dims,bounds:{min:box.min.toArray(),max:box.max.toArray()},uvSeam:'explicit 0..1 cylindrical seam on label',animations:animationReport,validation,limits:'18,000 triangles / 18 primitives / 1 MB. Original illustrative can; no food-safety or manufacturing claim.'};fs.mkdirSync(path.join(H,'reports'),{recursive:true});fs.writeFileSync(path.join(H,'reports/structure-motion.json'),JSON.stringify(result,null,2));console.log(JSON.stringify({status:result.status,sha256:result.sha256,bytes:result.bytes,triangles,primitives,dimensions:dims,validation:validation.issues},null,2));

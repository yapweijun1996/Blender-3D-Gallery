import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {readFile} from 'node:fs/promises';
import {validateBytes} from 'gltf-validator';
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';
import {Box3,Raycaster,Vector3} from 'three';
const id='provision-shop-pulley-tin-display';
const bytes=await readFile(process.argv[2]??new URL('./exports/'+id+'.glb',import.meta.url));
const raw=JSON.parse(bytes.subarray(20,20+bytes.readUInt32LE(12)));
const v=await validateBytes(new Uint8Array(bytes),{uri:id+'.glb'});
for(const k of ['numErrors','numWarnings','numInfos','numHints'])assert.equal(v.issues[k],0,JSON.stringify(v.issues));
assert.deepEqual(raw.buffers.map(x=>x.uri),[undefined]);
for(const k of ['images','animations','cameras'])assert.equal(raw[k]?.length??0,0);
const {scene}=await new GLTFLoader().parseAsync(bytes.buffer.slice(bytes.byteOffset,bytes.byteOffset+bytes.byteLength),'');
scene.updateMatrixWorld(true);
const exhibit=scene.getObjectByName('ABSTRACT_MUSEUM_PLINTH'),
 drum=scene.getObjectByName('OVERHEAD_TIMBER_AND_ONE_AUTHORED_PULLEY'),
 pair=scene.getObjectByName('PAIR_OPEN_EMPTY_PROVISION_TINS');
assert.ok(exhibit&&drum&&pair);
const part=(root,prefix)=>{
 const a=[];root.traverse(n=>{if(n.name.startsWith(prefix)&&!n.parent?.name.startsWith(prefix))a.push(n);});
 assert.equal(a.length,1,prefix);return a[0];};
const b=o=>new Box3().setFromObject(o,true);
const hit=(o,vec,di,far)=>new Raycaster(vec,di,0,far).intersectObject(o,true)[0]?.point;
const pulley=part(drum,'Single_sheave_with_real_recessed_cord_groove');
const rope=part(drum,'Single_continuous_cord_over_groove_between_vessels');
const mark=part(drum,'Continuous_pulley_shaft_through_both_cheeks');
assert.ok(b(pulley).intersectsBox(b(mark)));
const err=[];
const origin=new Vector3(0,1.152,.012);
for(let k=0;k<=48;k+=2){
 const a=k*Math.PI/48,d=new Vector3(Math.cos(a),Math.sin(a),0);
 const cord=hit(rope,origin.clone(),d,.199),groove=hit(pulley,origin.clone().addScaledVector(d,.218),d.clone().negate(),.055);
 assert.ok(cord&&groove,k);const gap=cord.clone().sub(groove).dot(d);
 assert.ok(gap>=-.00015&&gap<.00045,[k,gap].join());err.push(gap*1e3);
}
const tin=[];
for(const [tag,x,z] of [['HIGH',-.178,.720],['LOW',.178,.430]]){
 const p=pair.getObjectByName(tag+'_EMPTY_TIN');assert.ok(p);
 const tub=part(p,'Bored_empty_rolled_enamel_tub'),bail=part(p,'Continuous_ear-to-ear_formed_bail'),knot=part(p,'Seated_cord_lashing');
 const ears=p.children.filter(o=>o.name.startsWith('True_bored_eye_secured_outside_tin'));assert.equal(ears.length,2);
 assert.ok(b(bail).intersectsBox(b(knot))&&b(knot).intersectsBox(b(rope)));
 const holes=[];
 for(const o of ears){
  const c=b(o).getCenter(new Vector3());
  assert.ok(Math.min(Math.abs(b(o).min.x-x), Math.abs(b(o).max.x-x))-.1065>.002);
  const q=hit(o,new Vector3(c.x+.0064,c.y,c.z+.028),new Vector3(0,0,-1),.056);
  assert.equal(q,undefined);holes.push(c);
 }
 const floors=[];
 for(const [dx,dy] of [[0,0],[.037,-.032],[-.058,.028],[0,-.074]]){
  const q=hit(tub,new Vector3(x+dx,z+.204,.012-dy),new Vector3(0,-1,0),.200);
  assert.ok(q&&Math.abs(q.y-z-.012)<1.2e-5,JSON.stringify({tag,dx,dy,q}));
  floors.push(q.y);
 }
 tin.push({tag, openEmptyMouthRays:floors.length, separateExternalEarBores:holes.length,cavityBottomMeters:floors});
}
const bbox=b(scene),i=v.info;
console.log(JSON.stringify({sha256:createHash('sha256').update(bytes).digest('hex'),bytes:bytes.length,issues:v.issues,triangles:i.totalTriangleCount,vertices:i.totalVertexCount,drawCalls:i.drawCallCount,meshes:raw.meshes.length,materials:raw.materials.length,grooveSamples:err.length,grooveGapMinMaxMm:[Math.min(...err),Math.max(...err)],tin,bounds:[bbox.min.toArray(),bbox.max.toArray()]},null,2));

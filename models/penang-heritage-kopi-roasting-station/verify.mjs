import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {readFile} from 'node:fs/promises';
import {validateBytes} from 'gltf-validator';
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';
import {Box3,Raycaster,Vector3} from 'three';
const id='penang-heritage-kopi-roasting-station';
const bytes=await readFile(process.argv[2]??new URL('./exports/'+id+'.glb',import.meta.url));
const gltf=JSON.parse(bytes.subarray(20,20+bytes.readUInt32LE(12)));
const k=await validateBytes(new Uint8Array(bytes),{uri:id+'.glb'});
for(const key of ['numErrors','numWarnings','numInfos','numHints'])assert.equal(k.issues[key],0,JSON.stringify(k.issues));
assert.deepEqual(gltf.buffers.map(x=>x.uri),[undefined]);
for(const key of ['images','animations','cameras'])assert.equal(gltf[key]?.length??0,0);
const {scene:model}=await new GLTFLoader().parseAsync(bytes.buffer.slice(bytes.byteOffset,bytes.byteOffset+bytes.byteLength),'');
model.updateMatrixWorld(true);
for(const name of ['PENANG_ORIGINAL_KOPI_ROASTING_STATION_EXHIBIT','ROASTING_POT_STOVE_AND_OPEN_MASONRY_SECTION','INDEPENDENT_PAUSED_POT_AND_PADDLE_TOOLS','SEPARATE_DISPLAY_PULLEY_NOT_CONNECTED_TO_STOVE'])assert.ok(model.getObjectByName(name),name);
const matches=(prefix)=>{const a=[];model.traverse(n=>{if(n.isMesh&&n.name.startsWith(prefix))a.push(n)});return a;};
const cast=(at,v,m,far)=>new Raycaster(at,v,0,far).intersectObjects(m,false)[0];
const pot=matches('Genuinely_hollow_thick_cast_roast_pot');
const spool=matches('Deep_open_rope_groove');
const cord=matches('One_genuine_stationary_rope');
const brick=matches('Individual_original_curved_brick_joint');
assert.equal(pot.length,1);assert.equal(spool.length,1);assert.equal(cord.length,1);assert.ok(brick.length>85);
assert.equal(matches('Paired_rounded_parked_hardwood_paddle_blade').length,2);
const depths=[];
for(const r of [0,.062,.120,.196,.241,.273])for(const a of [0,Math.PI/3,Math.PI/2,Math.PI,3*Math.PI/2]){
 const h=cast(new Vector3(-.23+r*Math.cos(a),.78,-.038-r*Math.sin(a)),new Vector3(0,-1,0),pot,1);
 assert.ok(h&&h.point.y>.218&&h.point.y<.554,[r,a,h?.point.y]);depths.push(.608-h.point.y);
}
let archRays=0;
for(const x of [-.060,0,.060])for(const y of [.133,.168,.208]){
 const at=new Vector3(-.23+x,y,.462),to=new Vector3(0,0,-1);
 assert.equal(cast(at,to,brick,.49),undefined);
 assert.ok([-0.002,0,0.002].some(e=>cast(at.clone().add(new Vector3(e,0,0)),to,brick,1.01)));
 archRays++;
}
const arc=[];
const center=new Vector3(.649,.930,-.305);
for(let j=1;j<24;j++){
 const t=j*Math.PI/24, v=new Vector3(0,Math.sin(t),-Math.cos(t));
 const from=center.clone().addScaledVector(v,.098), to=v.clone().negate();
 const h=cast(from,to,spool,.095), rr=cast(from,to,cord,.075);
 assert.ok(rr&&h,[j,rr,h]);
 const line=rr.point.distanceTo(center),root=h.point.distanceTo(center);
 assert.ok(line>.0545&&line<.0577&&root>.0465&&root<.04715,[j,line,root]);
 arc.push(line);
}
const bbox=new Box3().setFromObject(model,true),info=k.info;
console.log(JSON.stringify({sha256:createHash('sha256').update(bytes).digest('hex'),bytes:bytes.length,issues:k.issues,triangles:info.totalTriangleCount,vertices:info.totalVertexCount,drawCalls:info.drawCallCount,meshes:gltf.meshes.length,materials:gltf.materials.length,cavityRays:depths.length,depthsMm:[Math.min(...depths)*1000,Math.max(...depths)*1000],archRays,actualRopeArcRays:arc.length,bounds:[bbox.min.toArray(),bbox.max.toArray()]},null,2));

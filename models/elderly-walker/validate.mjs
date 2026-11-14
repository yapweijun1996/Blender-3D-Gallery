import fs from 'node:fs';import path from 'node:path';import {fileURLToPath} from 'node:url';import {createHash} from 'node:crypto';import assert from 'node:assert/strict';import * as T from 'three';import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';import validator from 'gltf-validator';
const H=path.dirname(fileURLToPath(import.meta.url)),bytes=fs.readFileSync(path.join(H,'exports/elderly-walker.glb')),v=await validator.validateBytes(new Uint8Array(bytes));assert.equal(v.issues.numErrors,0);assert.equal(v.issues.numWarnings,0);
const raw=JSON.parse(bytes.subarray(20,20+bytes.readUInt32LE(12)));assert.ok(!raw.skins?.length&&!raw.images?.length&&raw.buffers.every(x=>!x.uri));
const g=await new GLTFLoader().parseAsync(bytes.buffer.slice(bytes.byteOffset,bytes.byteOffset+bytes.byteLength),'');g.scene.updateMatrixWorld(true);const node=n=>{const o=g.scene.getObjectByName(n);assert.ok(o,n);return o;};
let triangles=0,primitives=0;g.scene.traverse(o=>{if(o.isMesh){primitives++;triangles+=(o.geometry.index?.count??o.geometry.attributes.position.count)/3;assert.ok(Array.from(o.geometry.attributes.position.array).every(Number.isFinite));}});assert.ok(triangles<=15000&&bytes.length<=2000000&&primitives<=120);
const verts=o=>{const a=[];o.traverse(m=>{if(m.isMesh)for(let i=0;i<m.geometry.attributes.position.count;i++)a.push(new T.Vector3().fromBufferAttribute(m.geometry.attributes.position,i).applyMatrix4(m.matrixWorld));});return a;};
const feet=['Left','Right'],rest=feet.map(s=>verts(node(s+'Foot'))),box=new T.Box3().setFromObject(g.scene),size=box.getSize(new T.Vector3());assert.ok(Math.abs(box.min.y)<.002&&size.y>1.55&&size.y<1.7);
assert.deepEqual(g.animations.map(c=>c.name).sort(),['Idle','WalkInPlace']);
const results=[];
for(const c of g.animations){
 assert.ok(Math.abs(c.duration-2)<1e-5);
 for(const n of ['CharacterRoot','LeftHip','RightHip','LeftKnee','RightKnee','LeftFoot','RightFoot','LeftShoulder','RightShoulder'])for(const prop of ['position','quaternion'])assert.ok(c.tracks.some(t=>t.name===n+'.'+prop),'reset '+n);
 for(const t of c.tracks){assert.equal(t.times[0],0);assert.ok(Math.abs(t.times.at(-1)-2)<1e-6);const n=t.getValueSize();for(let i=0;i<n;i++)assert.ok(Math.abs(t.values[i]-t.values.at(-n+i))<1e-5);}
 const mix=new T.AnimationMixer(g.scene),a=mix.clipAction(c);a.setLoop(T.LoopOnce,1);a.clampWhenFinished=true;a.play();
 const samples=[];let stanceError=0,pathError=0,rootDrift=0,gripError=0;const clearance=[0,0],kneeMax=[0,0],hipMax=[0,0];
 for(let i=0;i<=60;i++){
  const time=i/30;mix.setTime(time);g.scene.updateMatrixWorld(true);
  const sample={time,feet:[]};
  for(let f=0;f<2;f++){
   const side=feet[f],u=side==='Right'?time:time-1,swing=c.name==='WalkInPlace'&&u>=0&&u<=1;
   const lift=swing?0.07*Math.sin(Math.PI*u)**2:0,foreaft=swing?-0.07*Math.sin(2*Math.PI*u):0,offset=new T.Vector3(0,lift,-foreaft);
   const actual=verts(node(side+'Foot')),expected=rest[f].map(v=>v.clone().add(offset)),error=Math.max(...actual.map((v,j)=>v.distanceTo(expected[j]))),floor=Math.min(...actual.map(v=>v.y));
   pathError=Math.max(pathError,error);if(!swing)stanceError=Math.max(stanceError,error);
   assert.ok(error<.0005,'actual foot vertices follow authored trajectory '+side+' '+time+' error '+error);assert.ok(floor>=-.0005,'no floor penetration');
   if(swing&&u>=.2&&u<=.8)assert.ok(floor>0.023100000000000002,'swing clearance');
   clearance[f]=Math.max(clearance[f],floor);const knee=node(side+'Knee').quaternion.angleTo(new T.Quaternion()),hip=node(side+'Hip').quaternion.angleTo(new T.Quaternion());kneeMax[f]=Math.max(kneeMax[f],knee);hipMax[f]=Math.max(hipMax[f],hip);assert.ok(knee<1.3&&hip<.8,'joint range');
   sample.feet.push({side,phase:swing?'swing':'stance',floor,vertexError:error,knee,hip});
  }
  rootDrift=Math.max(rootDrift,node('CharacterRoot').position.length());gripError=Math.max(gripError,node('HandGrip').getWorldPosition(new T.Vector3()).distanceTo(node('ToolGrip').getWorldPosition(new T.Vector3())));
  assert.ok(new T.Box3().setFromObject(node('PocketBook')).min.y>.25,'held prop floor clearance');
  samples.push(sample);
 }
 assert.ok(stanceError<1e-5&&rootDrift<1e-5&&gripError<1e-5);if(c.name==='WalkInPlace'){assert.ok(clearance.every(x=>x>0.065)&&kneeMax.every(x=>x>0.65)&&hipMax.every(x=>x>0.3),'real bilateral articulated gait');}
 results.push({clip:c.name,status:'PASS',samples:61,stance_vertex_error:stanceError,trajectory_vertex_error:pathError,root_drift:rootDrift,grip_error:gripError,max_clearance:clearance,max_knee_angle:kneeMax,max_hip_angle:hipMax,poses:samples});mix.stopAllAction();mix.uncacheRoot(g.scene);
}
const mix=new T.AnimationMixer(g.scene);for(const name of ['WalkInPlace','Idle','WalkInPlace','Idle']){mix.stopAllAction();const a=mix.clipAction(g.animations.find(c=>c.name===name));a.reset().setLoop(T.LoopOnce,1);a.clampWhenFinished=true;a.play();mix.setTime(0);g.scene.updateMatrixWorld(true);for(let f=0;f<2;f++)assert.ok(Math.max(...verts(node(feet[f]+'Foot')).map((v,j)=>v.distanceTo(rest[f][j])))<1e-5);mix.setTime(.5);}mix.stopAllAction();
const report={id:'elderly-walker',status:'PASS',sha256:createHash('sha256').update(bytes).digest('hex'),triangles,glb_bytes:bytes.length,primitives,dimensions:size.toArray(),clips:results,clip_switching:'PASS',limits:'Rigid articulated in-place stepping only, no root locomotion, skin, runtime IK or navigation. Physical mobile and Safari untested.'};fs.writeFileSync(path.join(H,'reports/assets.json'),JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify({id:report.id,status:report.status,triangles,bytes:bytes.length,walk:results.find(x=>x.clip==='WalkInPlace')},null,2));

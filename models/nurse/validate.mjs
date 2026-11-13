import fs from 'node:fs';import path from 'node:path';import {fileURLToPath} from 'node:url';import {createHash} from 'node:crypto';import assert from 'node:assert/strict';import * as T from 'three';import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';import validator from 'gltf-validator';
const H=path.dirname(fileURLToPath(import.meta.url)),contract=JSON.parse(fs.readFileSync(path.join(H,'contract.json'))),id=contract.id,bytes=fs.readFileSync(path.join(H,'exports',id+'.glb'));
const result=await validator.validateBytes(new Uint8Array(bytes));assert.equal(result.issues.numErrors,0);assert.equal(result.issues.numWarnings,0);
const raw=JSON.parse(bytes.subarray(20,20+bytes.readUInt32LE(12)));assert.ok(!raw.skins?.length&&!raw.images?.length);assert.ok(raw.buffers.every(x=>!x.uri));
const g=await new GLTFLoader().parseAsync(bytes.buffer.slice(bytes.byteOffset,bytes.byteOffset+bytes.byteLength),'');g.scene.updateMatrixWorld(true);
let triangles=0,primitives=0;g.scene.traverse(o=>{if(o.isMesh){primitives++;triangles+=(o.geometry.index?.count??o.geometry.attributes.position.count)/3;assert.ok(Array.from(o.geometry.attributes.position.array).every(Number.isFinite));}});
assert.ok(triangles<=15000&&bytes.length<=2000000&&primitives<=120);
const bounds=new T.Box3().setFromObject(g.scene),size=bounds.getSize(new T.Vector3());assert.ok(Math.abs(bounds.min.y)<.002&&size.y>1.65&&size.y<1.95);
const node=n=>{const o=g.scene.getObjectByName(n);assert.ok(o,n);return o;};
const verts=o=>{const v=[];o.traverse(m=>{if(m.isMesh)for(let i=0;i<m.geometry.attributes.position.count;i++)v.push(new T.Vector3().fromBufferAttribute(m.geometry.attributes.position,i).applyMatrix4(m.matrixWorld));});return v;};
const feet=['LeftFoot','RightFoot'].map(node),rest=feet.map(verts),eff=node(contract.effector),initialEff=eff.getWorldPosition(new T.Vector3());
assert.deepEqual(g.animations.map(c=>c.name).sort(),['Idle',contract.action].sort());
const reports=[];
for(const c of g.animations){
 assert.ok(Math.abs(c.duration-2)<1e-5);
 for(const n of ['CharacterRoot','HeadJoint','LeftShoulder','RightShoulder','LeftElbow','RightElbow','LeftHip','RightHip','LeftKnee','RightKnee'])for(const prop of ['position','quaternion'])assert.ok(c.tracks.some(t=>t.name===n+'.'+prop),'explicit reset '+n);
 for(const t of c.tracks){assert.ok(Math.abs(t.times[0])<1e-6&&Math.abs(t.times.at(-1)-2)<1e-6);const n=t.getValueSize();for(let i=0;i<n;i++)assert.ok(Math.abs(t.values[i]-t.values.at(-n+i))<1e-5,'raw endpoints');}
 const mixer=new T.AnimationMixer(g.scene),a=mixer.clipAction(c);a.setLoop(T.LoopOnce,1);a.clampWhenFinished=true;a.play();
 let drift=0,gripError=0,rootDrift=0,travel=0,jointMotion=0,headMotion=0;const samples=[];
 for(let i=0;i<=60;i++){
  mixer.setTime(i/30);g.scene.updateMatrixWorld(true);
  for(let f=0;f<2;f++){const vs=verts(feet[f]);drift=Math.max(drift,...vs.map((v,j)=>v.distanceTo(rest[f][j])));assert.ok(Math.abs(Math.min(...vs.map(v=>v.y)))<.002);}
  const grip=node('HandGrip').getWorldPosition(new T.Vector3());gripError=Math.max(gripError,grip.distanceTo(node('ToolGrip').getWorldPosition(new T.Vector3())));
  assert.ok(new T.Box3().setFromObject(node('RightGlove')).expandByScalar(.001).containsPoint(grip));
  assert.ok(new T.Box3().setFromObject(node('ToolGripGeometry')).expandByScalar(.001).containsPoint(grip));
  assert.ok(node('LeftHandGrip').getWorldPosition(new T.Vector3()).distanceTo(node('LeftToolGrip').getWorldPosition(new T.Vector3()))<1e-5,'left hand holds tray');const p=eff.getWorldPosition(new T.Vector3());travel=Math.max(travel,p.distanceTo(initialEff));rootDrift=Math.max(rootDrift,node('CharacterRoot').position.length());jointMotion=Math.max(jointMotion,node(contract.joint).quaternion.angleTo(new T.Quaternion()));headMotion=Math.max(headMotion,node('HeadJoint').quaternion.angleTo(new T.Quaternion()));
  assert.ok(new T.Box3().setFromObject(node('OccupationTool')).min.y>.12,'held tool above floor');
  if(id==='chef'){assert.ok(Math.hypot(p.x-.60,p.z-.36)<.16,'spoon remains within pot opening');assert.ok(p.y>.65&&p.y<.71,'spoon in cooking surface zone');}
  if(id==='teacher'){assert.ok(p.x>.6&&p.x<1.48&&p.y>1&&p.y<1.70&&p.z<.525,'pointer remains in front of board');}
  samples.push({time:i/30,effector:p.toArray()});
 }
 assert.ok(drift<1e-5&&rootDrift<1e-5&&gripError<1e-5);
 if(c.name===contract.action){assert.ok(jointMotion>=contract.amplitude-.002,'expected action rotation');assert.ok(travel>contract.minimum_travel,'occupation effector travel');}else assert.ok(headMotion>.06);
 reports.push({clip:c.name,status:'PASS',sample_count:61,transformed_foot_vertex_drift:drift,root_drift:rootDrift,grip_error:gripError,joint_rotation:jointMotion,effector_travel:travel,samples});
 mixer.stopAllAction();mixer.uncacheRoot(g.scene);
}
const mix=new T.AnimationMixer(g.scene);
for(const name of [contract.action,'Idle',contract.action,'Idle']){mix.stopAllAction();const a=mix.clipAction(g.animations.find(c=>c.name===name));a.reset().setLoop(T.LoopOnce,1);a.clampWhenFinished=true;a.play();mix.setTime(0);g.scene.updateMatrixWorld(true);assert.ok(node(contract.joint).quaternion.angleTo(new T.Quaternion())<1e-5);mix.setTime(.5);}
mix.stopAllAction();
const report={id,status:'PASS',sha256:createHash('sha256').update(bytes).digest('hex'),triangles,glb_bytes:bytes.length,primitives,dimensions:size.toArray(),clips:reports,clip_switching:'PASS',validator:{errors:0,warnings:0},limitations:'Rigid articulation only. Physical mobile/Safari untested.'};
fs.writeFileSync(path.join(H,'reports/assets.json'),JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify({id,status:'PASS',triangles,bytes:bytes.length,primitives}));

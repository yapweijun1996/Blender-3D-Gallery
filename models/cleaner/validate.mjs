import fs from 'node:fs';import path from 'node:path';import {fileURLToPath} from 'node:url';import {createHash} from 'node:crypto';import assert from 'node:assert/strict';import * as T from 'three';import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';import validator from 'gltf-validator';
const H=path.dirname(fileURLToPath(import.meta.url)),bytes=fs.readFileSync(path.join(H,'exports/cleaner.glb'));
const validation=await validator.validateBytes(new Uint8Array(bytes));assert.equal(validation.issues.numErrors,0);assert.equal(validation.issues.numWarnings,0);
const json=JSON.parse(bytes.subarray(20,20+bytes.readUInt32LE(12)));assert.ok(!json.images?.length&&!json.skins?.length&&!json.extensionsRequired?.length);assert.ok(json.buffers.every(b=>!b.uri));
const g=await new GLTFLoader().parseAsync(bytes.buffer.slice(bytes.byteOffset,bytes.byteOffset+bytes.byteLength),'');g.scene.updateMatrixWorld(true);
let triangles=0,primitives=0;g.scene.traverse(o=>{if(o.isMesh){primitives++;triangles+=(o.geometry.index?.count??o.geometry.attributes.position.count)/3;for(const n of o.geometry.attributes.position.array)assert.ok(Number.isFinite(n));}});
assert.ok(bytes.length<=2000000&&triangles<=15000&&primitives<=120,JSON.stringify({bytes:bytes.length,triangles,primitives}));
const bounds=new T.Box3().setFromObject(g.scene),size=bounds.getSize(new T.Vector3());assert.ok(Math.abs(bounds.min.y)<.002&&size.y>1.73&&size.y<1.77);
assert.deepEqual(g.animations.map(c=>c.name).sort(),['Idle','Sweep']);
const node=n=>{const o=g.scene.getObjectByName(n);assert.ok(o,n);return o;};
const joints=['CleanerRoot','HeadJoint','LeftShoulder','RightShoulder','LeftElbow','RightElbow','LeftHip','RightHip','LeftKnee','RightKnee'];
function vertices(o){const a=[];o.traverse(x=>{if(x.isMesh){const p=x.geometry.attributes.position;for(let i=0;i<p.count;i++)a.push(new T.Vector3().fromBufferAttribute(p,i).applyMatrix4(x.matrixWorld));}});return a;}
const feet=['LeftFoot','RightFoot'].map(n=>node(n)),footRest=feet.map(vertices),root=node('CleanerRoot');const clips=[];
function setup(c){const m=new T.AnimationMixer(g.scene),a=m.clipAction(c);a.setLoop(T.LoopOnce,1);a.clampWhenFinished=true;a.play();return m;}
for(const c of g.animations){
 assert.ok(Math.abs(c.duration-2)<.001,c.name+' duration');
 for(const n of joints)for(const p of ['position','quaternion'])assert.ok(c.tracks.some(t=>t.name===n+'.'+p),c.name+' reset '+n+'.'+p);
 for(const t of c.tracks){assert.ok(Math.abs(t.times[0])<.00001&&Math.abs(t.times.at(-1)-2)<.001);const k=t.getValueSize();for(let i=0;i<k;i++)assert.ok(Math.abs(t.values[i]-t.values[t.values.length-k+i])<.00001,'raw loop endpoints');}
 const m=setup(c);let maxFoot=0,maxGrip=0,maxFloor=0,maxRoot=0,shoulderMotion=0,headMotion=0;const brushCenters=[];
 for(let i=0;i<=40;i++){
  m.setTime(2*i/40);g.scene.updateMatrixWorld(true);
  for(let f=0;f<feet.length;f++){const vs=vertices(feet[f]);assert.equal(vs.length,footRest[f].length);maxFoot=Math.max(maxFoot,...vs.map((v,j)=>v.distanceTo(footRest[f][j])));assert.ok(Math.abs(Math.min(...vs.map(v=>v.y)))<.002);}
  const grip=node('HandGrip').getWorldPosition(new T.Vector3()),tg=node('ToolGrip').getWorldPosition(new T.Vector3());maxGrip=Math.max(maxGrip,grip.distanceTo(tg));
  assert.ok(new T.Box3().setFromObject(node('RightGlove')).expandByScalar(.001).containsPoint(grip),'grip within actual glove');
  assert.ok(new T.Box3().setFromObject(node('BroomHandle')).expandByScalar(.018).containsPoint(grip),'grip on actual handle bounds');
  const br=[];g.scene.traverse(o=>{if(o.name.startsWith('Bristle_'))br.push(...vertices(o));});const floor=Math.min(...br.map(v=>v.y));maxFloor=Math.max(maxFloor,Math.abs(floor));assert.ok(Math.min(...br.map(v=>v.y))>=-.002);
  brushCenters.push(new T.Box3().setFromObject(node('BroomHead')).getCenter(new T.Vector3()));maxRoot=Math.max(maxRoot,root.position.length());
  shoulderMotion=Math.max(shoulderMotion,node('RightShoulder').quaternion.angleTo(new T.Quaternion()));headMotion=Math.max(headMotion,node('HeadJoint').quaternion.angleTo(new T.Quaternion()));
 }
 assert.ok(maxFoot<.00001&&maxGrip<.00001&&maxFloor<.002&&maxRoot<.00001);
 const sweepSpan=Math.max(...brushCenters.map(v=>v.distanceTo(brushCenters[0])));
 if(c.name==='Sweep')assert.ok(shoulderMotion>.24&&sweepSpan>.12,'meaningful shoulder/tool sweep');else assert.ok(headMotion>.06,'meaningful idle head motion');
 clips.push({name:c.name,duration:c.duration,tracks:c.tracks.length,samples:41,max_transformed_foot_vertex_drift:maxFoot,max_grip_error:maxGrip,max_bristle_floor_error:maxFloor,max_root_drift:maxRoot,shoulder_rotation:shoulderMotion,head_rotation:headMotion,brush_sweep_span:sweepSpan});
 m.stopAllAction();m.uncacheRoot(g.scene);
}
const mix=new T.AnimationMixer(g.scene);for(const n of ['Sweep','Idle','Sweep','Idle']){mix.stopAllAction();const a=mix.clipAction(g.animations.find(c=>c.name===n));a.reset().setLoop(T.LoopOnce,1);a.clampWhenFinished=true;a.play();mix.setTime(0);g.scene.updateMatrixWorld(true);assert.ok(node('RightShoulder').quaternion.angleTo(new T.Quaternion())<1e-5,'clip switch resets unused limb');mix.setTime(.5);}
mix.stopAllAction();
const report={id:'cleaner',backlog_id:266,status:'PASS',sha256:createHash('sha256').update(bytes).digest('hex'),glb_bytes:bytes.length,triangles,primitives,budgets:{max_triangles:15000,max_glb_bytes:2000000,max_primitives:120},dimensions:size.toArray(),clips,clip_switching:'PASS',validation:{errors:0,warnings:0},limits:'Rigid articulated nodes, no skin/IK/navigation; physical mobile and Safari untested'};
fs.writeFileSync(path.join(H,'reports/assets.json'),JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report,null,2));

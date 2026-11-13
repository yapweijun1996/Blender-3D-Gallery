import fs from 'node:fs';import crypto from 'node:crypto';import * as T from 'three';import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';
globalThis.ProgressEvent=class{constructor(t,p){Object.assign(this,p)}};
const p='models/escalator/candidates/curved-dual-track/',b=fs.readFileSync(p+'exports/optimized.glb');
const g=await new GLTFLoader().parseAsync(b.buffer.slice(b.byteOffset,b.byteOffset+b.byteLength),'');
const mixer=new T.AnimationMixer(g.scene),actions=g.animations.map(c=>mixer.clipAction(c));actions.forEach(a=>{a.setLoop(T.LoopOnce,1);a.clampWhenFinished=true;a.play()});mixer.setTime(1/24);g.scene.updateMatrixWorld(true);
const steps=[];g.scene.traverse(o=>{if(/^STEP_\d+$/.test(o.name))steps.push(o)});steps.sort((a,b)=>a.name.localeCompare(b.name));
const bv=v=>[v.x,-v.z,v.y],v=new T.Vector3();
function vertices(o,mat){let a=o.geometry.attributes.position;return Array.from({length:a.count},(_,i)=>bv(v.fromBufferAttribute(a,i).applyMatrix4(mat)))}
const rails=[];g.scene.traverse(o=>{if(o.isMesh&&o.name.startsWith('TRACK_'))rails.push({name:o.name,vertices:vertices(o,o.matrixWorld),indices:Array.from(o.geometry.index.array)})});const fixed=[];g.scene.traverse(o=>{if(o.isMesh&&/^(LANDING|COMB|GUARD|SKIRT|TRUSS)/.test(o.name)){fixed.push({name:o.name,vertices:vertices(o,o.matrixWorld),indices:Array.from(o.geometry.index.array)})}});
const meshes=[];for(const s of steps){s.traverse(o=>{if(o.isMesh){const mat=new T.Matrix4().copy(s.matrixWorld).invert().multiply(o.matrixWorld);meshes.push({step:s.name,name:o.name,vertices:vertices(o,mat),indices:Array.from(o.geometry.index.array)})}})}
// Actual exported tracks through Three's interpolants; no analytic pose substitution.
const period=steps[0].userData.period_seconds,samples=[];
for(let f=0;f<=1200;f++){const t=1/24+period*f/1200;mixer.setTime(t);g.scene.updateMatrixWorld(true);samples.push(steps.map(s=>{const p=new T.Vector3(),q=new T.Quaternion(),scale=new T.Vector3();s.matrixWorld.decompose(p,q,scale);const dir=new T.Vector3(0,0,-1).applyQuaternion(q);return [...bv(p),Math.atan2(dir.y,-dir.z),...scale.toArray()]}))}
const clips=g.animations.map(c=>({name:c.name,duration:c.duration,tracks:c.tracks.map(t=>({name:t.name,times:Array.from(t.times),values:Array.from(t.values)}))}));
fs.writeFileSync(p+'reports/actual-glb-samples.json',JSON.stringify({sha256:crypto.createHash('sha256').update(b).digest('hex'),bytes:b.length,meshes,fixed,rails,samples,period,clips}));
console.log(JSON.stringify({bytes:b.length,meshes:meshes.length,steps:steps.length,fixed:fixed.length,samples:samples.length,period,clips:clips.map(c=>[c.name,c.duration])}));


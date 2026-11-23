// Usage: node test_finger_rig.mjs CHARACTER.glb REPORT.json
// Verify five independently controlled finger meshes per hand in Three.js.
// No textures or browser rendering; original artifact is read-only.
import fs from 'node:fs';
import crypto from 'node:crypto';
import {pathToFileURL} from 'node:url';
const [input,output]=process.argv.slice(2);if(!input||!output)throw Error('Expected input and report');
const hash=p=>crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex');const before=hash(input);
const dir=process.env.THREE_DIR||'/tmp/gjh-hair-three/node_modules/three';
const THREE=await import(pathToFileURL(`${dir}/build/three.module.js`));
const {GLTFLoader}=await import(pathToFileURL(`${dir}/examples/jsm/loaders/GLTFLoader.js`));
globalThis.self??=globalThis;globalThis.ProgressEvent??=class ProgressEvent{constructor(type,props={}){this.type=type;Object.assign(this,props);}};
const loader=new GLTFLoader();loader.register(()=>({name:'NoTextureDecoder',loadTexture:()=>Promise.resolve(new THREE.Texture())}));
const bytes=fs.readFileSync(input),g=await loader.parseAsync(bytes.buffer.slice(bytes.byteOffset,bytes.byteOffset+bytes.byteLength),'');
g.scene.updateMatrixWorld(true);const bones=[],slotOwners=[];
g.scene.traverse(o=>{if(o.isBone)bones.push(o);if(typeof o.userData?.partSlot==='string'&&o.userData.partSlot.startsWith('Finger_'))slotOwners.push(o);});
const fingerParts=[];
for(const side of ['L','R'])for(const finger of ['Index','Middle','Ring','Pinky','Thumb']){
 const slot=`Finger_${finger}_${side}`,owners=slotOwners.filter(o=>o.userData.partSlot===slot);
 if(owners.length!==1)throw Error(`Expected exactly one slot owner ${slot}, got ${owners.length}`);
 const owner=owners[0],mesh=[];owner.traverse(o=>{if(o.isMesh)mesh.push(o);});if(mesh.length!==1||!mesh[0].isSkinnedMesh)throw Error(`Expected one skinned mesh ${slot}`);
 const expected=`Finger.${finger}.${side}`,clean=THREE.PropertyBinding.sanitizeNodeName(expected);
 const matches=bones.filter(b=>b.name===expected||b.name===clean);
 if(matches.length!==1)throw Error(`Expected one bone ${expected} / ${clean}; got ${matches.length}`);
 fingerParts.push({slot,owner,mesh:mesh[0],bone:matches[0]});
}
function sample(mesh){const a=mesh.geometry.attributes.position,pt=new THREE.Vector3(),points=[];for(let i=0;i<a.count;i++){mesh.getVertexPosition(i,pt);mesh.localToWorld(pt);points.push(pt.clone());}return points;}
function movement(a,b){if(a.length!==b.length)throw Error('changed vertex count');return Math.max(...a.map((p,i)=>p.distanceTo(b[i])));}
const baseline=new Map(fingerParts.map(x=>[x.slot,sample(x.mesh)]));const checks=[];
for(const active of fingerParts){
 const old=active.bone.quaternion.clone();active.bone.rotateX(Math.PI/6);g.scene.updateMatrixWorld(true);
 const moved=movement(baseline.get(active.slot),sample(active.mesh));
 const other=Math.max(...fingerParts.filter(x=>x!==active).map(x=>movement(baseline.get(x.slot),sample(x.mesh))));
 active.bone.quaternion.copy(old);g.scene.updateMatrixWorld(true);
 const vis=active.owner.visible;active.owner.visible=false;const isolatedHidden=!active.owner.visible&&fingerParts.filter(x=>x!==active).every(x=>x.owner.visible);active.owner.visible=vis;
 checks.push({slot:active.slot,bone:active.bone.name,own_max_m:moved,other_max_m:other,isolatedHidden});
}
const animations=g.animations.map(a=>a.name),missing=['idle','walk','run','sit','stand_up'].filter(n=>!animations.includes(n));
const pass=checks.length===10&&checks.every(c=>c.own_max_m>1e-4&&c.other_max_m<1e-5&&c.isolatedHidden)&&missing.length===0&&hash(input)===before;
const report={status:pass?'PASS':'FAIL',sha256:before,three:'0.187.0',checks,animations,missing,limitations:['Node GLTFLoader structure/skin math only; no visual or browser rendering.','Each finger is a rigid one-segment joint, not a multi-joint anatomically articulated finger.','One X-axis rotation per finger; full range of motion and gesture/hand intersections not tested.']};
fs.writeFileSync(output,JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify({status:report.status,sha256:before,checks,animations,missing}));if(!pass)process.exitCode=1;

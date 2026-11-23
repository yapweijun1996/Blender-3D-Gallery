// Test matching character and skinned slot modules, including multi-bone slots.
// Usage: node test_module_rig.mjs CHARACTER.glb MODULES/manifest.json REPORT.json
// Requires Three.js 0.187.0 in THREE_DIR or /tmp/gjh-hair-three/node_modules/three.
// In Node only; textures are stubbed and no rendered/browser result is implied.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {pathToFileURL} from 'node:url';
const [characterPath,manifestPath,reportPath]=process.argv.slice(2);
if(!characterPath||!manifestPath||!reportPath)throw Error('Expected character, manifest, report');
const hash=p=>crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex');
const hashArray=a=>crypto.createHash('sha256').update(Buffer.from(a.buffer,a.byteOffset,a.byteLength)).digest('hex');
const dir=process.env.THREE_DIR||'/tmp/gjh-hair-three/node_modules/three';
const THREE=await import(pathToFileURL(`${dir}/build/three.module.js`));
const {GLTFLoader}=await import(pathToFileURL(`${dir}/examples/jsm/loaders/GLTFLoader.js`));
globalThis.self??=globalThis;
globalThis.ProgressEvent??=class ProgressEvent {constructor(type,props={}){this.type=type;Object.assign(this,props);}};
const loader=new GLTFLoader();loader.register(()=>({name:'NoTextureDecoder',loadTexture:()=>Promise.resolve(new THREE.Texture())}));
async function load(file){const b=fs.readFileSync(file);return loader.parseAsync(b.buffer.slice(b.byteOffset,b.byteOffset+b.byteLength),'');}
const manifest=JSON.parse(fs.readFileSync(manifestPath));
const baseline={character:hash(characterPath),manifest:hash(manifestPath)};
const character=await load(characterPath);character.scene.updateMatrixWorld(true);
const charBones=new Map();character.scene.traverse(o=>{if(o.isBone){if(charBones.has(o.name))throw Error(`Duplicate bone ${o.name}`);charBones.set(o.name,o);}});
function meshes(root){const out=[];root.traverse(o=>{if(o.isMesh)out.push(o);});return out;}
function taggedMeshes(root,slot){const set=new Set();root.traverse(o=>{if(o.userData?.partSlot===slot)o.traverse(q=>{if(q.isMesh)set.add(q);});});return [...set];}
function bones(root){const out=new Map();root.traverse(o=>{if(o.isBone)out.set(o.name,o);});return out;}
function signature(mesh){const p=mesh.geometry.attributes.position;if(!p||!p.array)throw Error(`Missing position on ${mesh.name}`);return `${p.count}:${hashArray(p.array)}`;}
function distance(a,b){
 const aa=a.geometry.attributes.position,bb=b.geometry.attributes.position;if(aa.count!==bb.count)throw Error('vertex count mismatch');
 let max=0,sum=0;const va=new THREE.Vector3(),vb=new THREE.Vector3();
 for(let i=0;i<aa.count;i++){a.getVertexPosition(i,va);a.localToWorld(va);b.getVertexPosition(i,vb);b.localToWorld(vb);let d=va.distanceTo(vb);if(!Number.isFinite(d))throw Error('Non-finite positions');max=Math.max(max,d);sum+=d;}
 return {max_m:max,mean_m:sum/aa.count,vertices:aa.count};
}
function worldPositions(meshes){
 const out=[];const p=new THREE.Vector3();
 for(const mesh of meshes){const count=mesh.geometry.attributes.position.count;for(let i=0;i<count;i++){mesh.getVertexPosition(i,p);mesh.localToWorld(p);out.push(p.clone());}}
 return out;
}
function displacement(a,b){if(a.length!==b.length)throw Error('Position sample size changed');let max=0;for(let i=0;i<a.length;i++)max=Math.max(max,a[i].distanceTo(b[i]));return max;}
function meshPairs(left,right){
 const bins=new Map();for(const mesh of right){const sig=signature(mesh);if(!bins.has(sig))bins.set(sig,[]);bins.get(sig).push(mesh);}
 return left.map(mesh=>{const sig=signature(mesh),bucket=bins.get(sig);return {left:mesh,right:bucket?.shift()||null,signature:sig};});
}
const limit=1e-5,report={status:'PENDING',three:'0.187.0',sha256:baseline,threshold_m:limit,modules:{},limitations:['Three.js GLTFLoader in Node with texture decoding stubbed; no rendered, material, or browser validation.','Five evenly spaced samples per animation plus one mixed head rotation; no continuous motion, contact, or full range-of-motion validation.','Character slot geometry must match the independently exported module in position ordering.','For optional modules, independent module skeleton is driven by matching character bone local transforms; no original character mesh exists for comparison.']};
let pass=true;
for(const [slot,entry] of Object.entries(manifest.modules)){
 const modulePath=path.join(path.dirname(manifestPath),entry.file);
 const moduleHash=fs.existsSync(modulePath)?hash(modulePath):null;
 try{
  const [replacement,reference]=await Promise.all([load(modulePath),load(modulePath)]);
  character.scene.add(replacement.scene,reference.scene);character.scene.updateMatrixWorld(true);
  const modMeshes=meshes(replacement.scene),refMeshes=meshes(reference.scene),refBones=bones(reference.scene);
  if(!modMeshes.length||modMeshes.length!==refMeshes.length)throw Error('Module mesh count mismatch');
  for(const mesh of modMeshes){
   if(!mesh.isSkinnedMesh)throw Error(`Expected a skinned mesh: ${mesh.name}`);
   const missing=mesh.skeleton.bones.filter(b=>!charBones.has(b.name)).map(b=>b.name);if(missing.length)throw Error(`Missing character bones ${missing.join(', ')}`);
   mesh.skeleton.bones=mesh.skeleton.bones.map(b=>charBones.get(b.name));
  }
  // The independent reference skeleton stays in its own GLB hierarchy and
  // receives the animated character's local bone transforms at each sample.
  function syncReference(){
   for(const [name,b] of refBones){const c=charBones.get(name);if(!c)throw Error(`Reference missing character bone ${name}`);b.position.copy(c.position);b.quaternion.copy(c.quaternion);b.scale.copy(c.scale);}
   character.scene.updateMatrixWorld(true);
  }
  const refPairs=meshPairs(modMeshes,refMeshes);
  if(refPairs.some(p=>!p.right))throw Error('Replacement and independent reference differ in geometry');
  const existing=taggedMeshes(character.scene,slot).filter(o=>!modMeshes.includes(o)&&!refMeshes.includes(o));
  const charPairs=meshPairs(existing,modMeshes);
  const exactExisting=charPairs.length>0&&charPairs.every(p=>p.right)&&charPairs.length===modMeshes.length;
  if(!entry.optional&&!exactExisting)throw Error(`Original slot geometry mismatch: original ${existing.length}, replacement ${modMeshes.length}`);
  function sample(label){
   syncReference();
   const independent=refPairs.map(p=>distance(p.left,p.right));
   const original=exactExisting?charPairs.map(p=>distance(p.left,p.right)):[];
   return {label,independent_max_m:Math.max(...independent.map(x=>x.max_m)),original_max_m:original.length?Math.max(...original.map(x=>x.max_m)):null};
  }
  const samples=[sample('rest')],clipMotion={};
  for(const name of ['idle','walk','run','sit','stand_up']){
   const clip=character.animations.find(c=>c.name===name);if(!clip)throw Error(`Missing animation ${name}`);
   const mixer=new THREE.AnimationMixer(character.scene);const action=mixer.clipAction(clip);action.setLoop(THREE.LoopOnce,1);action.clampWhenFinished=true;action.play();
   let clipStart=null, maxDisplacement=0;
   for(const f of [0,.25,.5,.75,1]){mixer.setTime(f*clip.duration);samples.push(sample(`${name}:${f}`));const current=worldPositions(modMeshes);if(!clipStart)clipStart=current;else maxDisplacement=Math.max(maxDisplacement,displacement(clipStart,current));}
   clipMotion[name]={duration_s:clip.duration,max_sampled_displacement_m:maxDisplacement};
   action.stop();mixer.stopAllAction();mixer.uncacheRoot(character.scene);
  }
  const head=charBones.get('Head');if(!head)throw Error('Missing head bone');const oldHead=head.quaternion.clone();head.rotateX(12*Math.PI/180);head.rotateY(-17*Math.PI/180);head.rotateZ(8*Math.PI/180);samples.push(sample('head:12,-17,8'));head.quaternion.copy(oldHead);character.scene.updateMatrixWorld(true);
  // Simulate switching an existing part for the module without altering files.
  const flags=existing.map(o=>o.visible);for(const mesh of existing)mesh.visible=false;replacement.scene.visible=true;
  const swap=existing.every(o=>!o.visible)&&replacement.scene.visible;
  existing.forEach((o,i)=>{o.visible=flags[i];});replacement.scene.visible=false;
  const max=Math.max(...samples.map(s=>Math.max(s.independent_max_m,s.original_max_m||0)));
  const unchanged=moduleHash===hash(modulePath);
  const ok=max<limit&&swap&&unchanged;
  report.modules[slot]={status:ok?'PASS':'FAIL',file:entry.file,sha256:moduleHash,inputs_unchanged:unchanged,optional:Boolean(entry.optional),mesh_count:modMeshes.length,source_mesh_count:existing.length,source_geometry_match:exactExisting,bones:entry.bones,samples,clipMotion,swap,max_m:max};
  if(!ok)pass=false;
  character.scene.remove(replacement.scene,reference.scene);replacement.scene.traverse(o=>{if(o.geometry)o.geometry.dispose();});reference.scene.traverse(o=>{if(o.geometry)o.geometry.dispose();});
 }catch(e){report.modules[slot]={status:'FAIL',file:entry.file,sha256:fs.existsSync(modulePath)?hash(modulePath):null,error:String(e)};pass=false;}
}
report.inputs_unchanged=hash(characterPath)===baseline.character&&hash(manifestPath)===baseline.manifest;
report.status=pass&&report.inputs_unchanged?'PASS':'FAIL';
fs.writeFileSync(reportPath,JSON.stringify(report,null,2)+'\n');
console.log(JSON.stringify({status:report.status,character:baseline.character,modules:Object.fromEntries(Object.entries(report.modules).map(([k,v])=>[k,{status:v.status,max_m:v.max_m,error:v.error}]))}));
if(report.status!=='PASS')process.exitCode=1;

import assert from 'node:assert/strict';import fs from 'node:fs';import {fileURLToPath} from 'node:url';import {createHash} from 'node:crypto';import {Box3,Vector3,AnimationMixer,LoopOnce} from 'three';import validator from 'gltf-validator';import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';
const dir=fileURLToPath(new URL('.',import.meta.url)),spec=JSON.parse(fs.readFileSync(dir+'backlog.json')),budget=spec.budget;
const bytes=fs.readFileSync(dir+'exports/optimized.glb'),json=JSON.parse(bytes.subarray(20,20+bytes.readUInt32LE(12)));
const gltf=await new GLTFLoader().parseAsync(bytes.buffer.slice(bytes.byteOffset,bytes.byteOffset+bytes.byteLength),'');const scene=gltf.scene;scene.updateMatrixWorld(true);
const v=await validator.validateBytes(new Uint8Array(bytes));assert.equal(v.issues.numErrors,0);assert.equal(v.issues.numWarnings,0);
const root=scene.getObjectByName(spec.root);assert.ok(root);assert.deepEqual(root.position.toArray(),[0,0,0]);assert.equal(root.userData.units,'metres');assert.ok(json.buffers.every(x=>!x.uri));assert.ok(!json.textures?.length&&!json.images?.length&&!json.cameras?.length&&!json.extensions?.KHR_lights_punctual);
let triangles=0,vertices=0;const parts={};scene.traverse(o=>{if(o.isMesh){const a=o.geometry.attributes.position;assert.ok(o.geometry.attributes.normal);vertices+=a.count;triangles+=(o.geometry.index?.count??a.count)/3;for(const x of a.array)assert.ok(Number.isFinite(x));const b=new Box3().setFromObject(o);parts[o.name]={min:b.min.toArray(),max:b.max.toArray()};}});
assert.ok(bytes.length<=budget.bytes,'fixed byte budget');assert.ok(triangles<=budget.triangles,'fixed polygon budget');assert.ok(Object.keys(parts).length<=budget.mesh_primitives,'fixed mesh primitive budget');assert.ok(Object.keys(parts).length>=4);
const bounds=new Box3().setFromObject(scene,true),dimensions=bounds.getSize(new Vector3()).toArray();
const ranges={23:[[.5,.8],[.95,1.15]],24:[[1.19,1.21],[.76,.79]],25:[[.55,.57],[.51,.55]],26:[[.33,.35],[.24,.29]],27:[[2.39,2.41],[.77,.80]],28:[[.45,.60],[.85,1.05]],31:[[.42,.45],[.37,.41]],32:[[.52,.55],[.97,1.02]],33:[[1.39,1.42],[1.60,1.65]],35:[[.47,.50],[.43,.60]],36:[[.65,.75],[1.95,2.02]],40:[[1.1,1.16],[1.85,1.95]],142:[[1.19,1.21],[.17,.19]],145:[[.6,.8],[1.15,1.3]],148:[[2.4,2.6],[2.58,2.61]],155:[[.23,.27],[.64,.67]]};
for(let i=0;i<2;i++)assert.ok(dimensions[i]>=ranges[spec.id][i][0]&&dimensions[i]<=ranges[spec.id][i][1],spec.id+' dimension '+i+': '+dimensions[i]);
assert.ok(bounds.min.y>=-.01,'metre ground datum');assert.ok(bounds.min.y<.011,'floor contact');
const required={23:['SEAT','BACK','CASTER'],24:['TOP','LEG'],25:['DISPLAY','STAND'],26:['KEYBOARD_Keys','MOVABLE_Lid'],27:['TOP'],28:['SEAT','BACK'],31:['BODY'],32:['MOVABLE_Drawer'],33:['BOARD'],35:['GROUP'],36:['MOVABLE_RackDoor'],40:['MOVABLE_LockerDoor'],142:['TOP'],145:['MOVABLE_Forks'],148:['MOVABLE_ContainerDoor','SIDE_CorrugatedRibs'],155:['BODY_Cylinder','HOSE','GAUGE']};
for(const prefix of required[spec.id]||[])assert.ok((()=>{let found=false;scene.traverse(o=>{if(o.name.startsWith(prefix))o.traverse(c=>{if(c.isMesh)found=true;});});return found;})(),'required independently editable feature '+prefix);
let animationTest='NOT APPLICABLE: static asset, no fabricated clips';
const counts={26:1,32:3,36:1,40:2,145:3,148:2};
if(counts[spec.id]){
 assert.equal(gltf.animations.length,counts[spec.id]);const moving=[];scene.traverse(o=>{if(o.name.startsWith('MOVABLE_'))moving.push(o);});assert.equal(moving.length,counts[spec.id]);
 const initial=moving.map(o=>({p:o.position.clone(),q:o.quaternion.clone(),scale:o.scale.clone(),box:new Box3().setFromObject(o,true)}));const mixer=new AnimationMixer(scene);
 for(const clip of gltf.animations){assert.ok(Math.abs(clip.duration-2.5)<1e-5);for(const t of clip.tracks){const n=t.getValueSize();assert.ok(Math.abs(t.times[0]-1/24)<1e-5);assert.ok(Math.abs(t.times.at(-1)-2.5)<1e-5);for(let i=0;i<n;i++)assert.ok(Math.abs(t.values[i]-t.values[t.values.length-n+i])<1e-5,'raw endpoint restoration');}const action=mixer.clipAction(clip);action.setLoop(LoopOnce,1);action.clampWhenFinished=true;action.play();}
 mixer.setTime(1.25);scene.updateMatrixWorld(true);const open=moving.map(o=>new Box3().setFromObject(o,true));
 moving.forEach((o,i)=>{const old=initial[i];
 if(spec.id===32){assert.ok(Math.abs(o.position.z-old.p.z-.35)<.001,'drawer frontwards travel');assert.ok(Math.abs(o.position.x-old.p.x)<1e-6);assert.ok(open[i].min.x>-.235&&open[i].max.x<.235,'drawer clears side-wall interior');}
 else if(spec.id===145&&o.name.startsWith('MOVABLE_LoadLink')){assert.ok(Math.abs(o.position.y-old.p.y-.06)<.001);assert.ok(Math.abs(o.scale.y-1.96)<.001);assert.ok(Math.abs(open[i].min.y-.055)<.001&&Math.abs(open[i].max.y-.30)<.001,'support remains joined to roller and raised fork');}
 else if(spec.id===145){assert.ok(Math.abs(o.position.y-old.p.y-.12)<.001,'pallet lifting stroke');const forks=[];o.traverse(x=>{if(x.name.startsWith('FORK'))forks.push(new Box3().setFromObject(x,true));});assert.equal(forks.length,2);assert.ok(forks.every(b=>b.min.y>.27),'raised forks clear floor and rollers');}
 else {const expected={26:1.12,36:1.2,40:1.25,148:1.3}[spec.id];assert.ok(Math.abs(old.q.angleTo(o.quaternion)-expected)<.001,'specified hinge angle');assert.ok(o.position.distanceTo(old.p)<1e-6,'fixed hinge');}
 });
 if(spec.id===26){const base=new Box3().setFromObject(scene.getObjectByName('BASE_Chassis'),true);assert.ok(open[0].min.y>base.max.y+.015,'closed lid clears base');}
 if(spec.id===36)assert.ok(.32-open[0].max.x>.30,'server access aperture');
 if(spec.id===40)for(let i=0;i<2;i++)assert.ok((moving[i].position.x+.49)-open[i].max.x>.30,'locker access aperture');
 if(spec.id===148){const sorted=open.slice().sort((a,b)=>a.min.x-b.min.x);assert.ok(sorted[1].min.x-sorted[0].max.x>1.6,'opposing doors open central aperture');assert.ok(open.every((b,i)=>b.min.z>initial[i].box.min.z-.001),'doors swing outward');assert.ok(open.every(b=>b.min.y>.14&&b.max.y<2.47),'doors clear floor and roof');}
 mixer.setTime(2.5);scene.updateMatrixWorld(true);moving.forEach((o,i)=>{assert.ok(o.position.distanceTo(initial[i].p)<.001);assert.ok(o.quaternion.angleTo(initial[i].q)<.001);});moving.forEach((o,i)=>assert.ok(o.scale.distanceTo(initial[i].scale)<.001,'scale restores'));mixer.stopAllAction();
 animationTest='PASS: raw 1/24–2.5s track endpoints, intended midpoint hinge/travel and measured opening/clearance, LoopOnce restoration; no physical equipment functionality implied';
}else assert.equal(gltf.animations.length,0);
const report={id:spec.title,backlog_id:spec.id,sha256:createHash('sha256').update(bytes).digest('hex'),glb_bytes:bytes.length,triangles,vertices,primitives:Object.keys(parts).length,materials:json.materials.length,textures:0,animations:gltf.animations.length,animationTest,dimensions,bounds:{min:bounds.min.toArray(),max:bounds.max.toArray()},parts,budget,validation:{errors:0,warnings:0,validator:v.validatorVersion},result:'PASS'};
fs.writeFileSync(dir+'reports/assets.json',JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report));

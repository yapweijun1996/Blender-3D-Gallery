import assert from 'node:assert/strict';import fs from 'node:fs';import {fileURLToPath} from 'node:url';import {createHash} from 'node:crypto';import {Box3,Vector3,AnimationMixer,LoopOnce} from 'three';import validator from 'gltf-validator';import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';
const dir=fileURLToPath(new URL('.',import.meta.url)),spec=JSON.parse(fs.readFileSync(dir+'backlog.json')),budget=spec.budget;
const bytes=fs.readFileSync(dir+'exports/optimized.glb'),json=JSON.parse(bytes.subarray(20,20+bytes.readUInt32LE(12)));
const gltf=await new GLTFLoader().parseAsync(bytes.buffer.slice(bytes.byteOffset,bytes.byteOffset+bytes.byteLength),'');const scene=gltf.scene;scene.updateMatrixWorld(true);
const v=await validator.validateBytes(new Uint8Array(bytes));assert.equal(v.issues.numErrors,0);assert.equal(v.issues.numWarnings,0);
const root=scene.getObjectByName(spec.root);assert.ok(root);assert.deepEqual(root.position.toArray(),[0,0,0]);assert.equal(root.userData.units,'metres');assert.ok(json.buffers.every(x=>!x.uri));assert.ok(!json.textures?.length&&!json.images?.length&&!json.cameras?.length&&!json.extensions?.KHR_lights_punctual);
let triangles=0,vertices=0;const parts={};scene.traverse(o=>{if(o.isMesh){const a=o.geometry.attributes.position;assert.ok(o.geometry.attributes.normal);vertices+=a.count;triangles+=(o.geometry.index?.count??a.count)/3;for(const x of a.array)assert.ok(Number.isFinite(x));const b=new Box3().setFromObject(o);parts[o.name]={min:b.min.toArray(),max:b.max.toArray()};}});
assert.ok(bytes.length<=budget.bytes,'fixed byte budget');assert.ok(triangles<=budget.triangles,'fixed polygon budget');assert.ok(Object.keys(parts).length<=budget.mesh_primitives,'fixed mesh primitive budget');assert.ok(Object.keys(parts).length>=4);
const bounds=new Box3().setFromObject(scene,true),dimensions=bounds.getSize(new Vector3()).toArray();
const ranges={11:[[.57,.64],[1.04,1.06]],12:[[.45,.47],[.41,.44]],51:[[1.89,1.91],[.94,.99]],52:[[1.39,1.41],[.75,.77]],53:[[.93,.95],[.89,.91]],54:[[.62,.64],[1.87,1.89]],55:[[1.69,1.71],[1.11,1.13]],56:[[1.19,1.21],[1.99,2.01]],57:[[.53,.55],[1.03,1.04]],59:[[1.13,1.15],[1.43,1.45]],60:[[.89,.91],[1.03,1.05]],90:[[.42,.44],[.32,.34]],91:[[.64,.66],[1.00,1.02]],93:[[.45,.47],[.89,.91]],95:[[.44,.46],[.70,.72]],124:[[1.94,1.97],[1.37,1.40]]};
for(let i=0;i<2;i++)assert.ok(dimensions[i]>=ranges[spec.id][i][0]&&dimensions[i]<=ranges[spec.id][i][1],spec.id+' dimension '+i+': '+dimensions[i]);
assert.ok(bounds.min.y>=-.01&&bounds.min.y<.011,'metre floor datum/contact');
const required={11:['BASKET_WireLattice','CASTER_Wheel','HANDLE_Grip'],12:['BASKET_SlottedWalls','MOVABLE_Handle'],51:['SEAT_Cushion','BACK_Cushion','ARM'],52:['TOP','APRON','LEG'],53:['COUNTER_Top','MOVABLE_Door','SHELF'],54:['INTERIOR_Shelf','MOVABLE_Door'],55:['MATTRESS','PILLOW','HEADBOARD'],56:['HANGING_Rail','MOVABLE_Door'],57:['BASIN_Hollow','FAUCET','PEDESTAL','DRAIN_Dark'],59:['MAIL_Slot','MOVABLE_Door','EDITABLE_Number'],60:['VENT_Inset','BODY_Shelf','MOVABLE_Door'],90:['BODY_Hollow','INNER_Pot','MOVABLE_Lid'],91:['WELL_Rim','BASKET_Wires','CONTROL_Knob'],93:['SEAT','BACK_Slat','LEG'],95:['TANK_Frosted','TAP_Nozzle','MOVABLE_Lid'],124:['CONVEYOR_Belt','SCANNER_Window','POS_Screen','BAG_Hook','MOVABLE_CashDrawer']};
for(const prefix of required[spec.id])assert.ok((()=>{let yes=false;scene.traverse(o=>{if(o.name.startsWith(prefix))o.traverse(c=>{if(c.isMesh)yes=true;});});return yes;})(),'required real editable mesh/group '+prefix);
if(spec.id===57){const drain=new Box3().setFromObject(scene.getObjectByName('DRAIN_Dark'),true),pedestal=new Box3().setFromObject(scene.getObjectByName('PEDESTAL'),true);assert.ok(drain.min.y>pedestal.max.y&&drain.max.y<.735,'drain above pedestal and below bowl rim');}
const counts={12:2,53:2,54:2,56:2,59:6,60:2,90:1,91:2,95:2,124:1};
let animationTest='NOT APPLICABLE: static asset, no fabricated animation';
if(counts[spec.id]){
 assert.equal(gltf.animations.length,counts[spec.id]);const moving=[];scene.traverse(o=>{if(o.name.startsWith('MOVABLE_'))moving.push(o);});assert.equal(moving.length,counts[spec.id]);
 const initial=moving.map(o=>({p:o.position.clone(),q:o.quaternion.clone(),s:o.scale.clone(),box:new Box3().setFromObject(o,true)}));const mixer=new AnimationMixer(scene);
 for(const clip of gltf.animations){assert.ok(Math.abs(clip.duration-2.5)<1e-5);for(const t of clip.tracks){const n=t.getValueSize();assert.ok(Math.abs(t.times[0]-1/24)<1e-5);assert.ok(Math.abs(t.times.at(-1)-2.5)<1e-5);for(let i=0;i<n;i++)assert.ok(Math.abs(t.values[i]-t.values[t.values.length-n+i])<1e-5,'raw endpoint equality without wrapping');}const action=mixer.clipAction(clip);action.setLoop(LoopOnce,1);action.clampWhenFinished=true;action.play();}
 mixer.setTime(1.25);scene.updateMatrixWorld(true);const open=moving.map(o=>new Box3().setFromObject(o,true));
 moving.forEach((o,i)=>{const old=initial[i];
  if(spec.id===91){assert.ok(Math.abs(o.position.y-old.p.y-.16)<.001,'basket lift');assert.ok(open[i].min.y>.94,'basket clears well');}
  else if(spec.id===124){assert.ok(Math.abs(o.position.z-old.p.z-.28)<.001,'drawer forward travel');assert.ok(open[i].min.x>-.26&&open[i].max.x<.26,'drawer clears side interiors');}
  else {assert.ok(Math.abs(old.q.angleTo(o.quaternion)-([12,90].includes(spec.id)?1.35:1.3))<.001,'exact hinge angle');assert.ok(o.position.distanceTo(old.p)<1e-6,'fixed hinge');}
 });
 if([53,54,56,59,60].includes(spec.id)){
  const descendants=new Set();moving.forEach(o=>o.traverse(x=>descendants.add(x)));const fixed=[];scene.traverse(o=>{if(o.isMesh&&!descendants.has(o)&&/^(BODY_|SHELF|COUNTER_)/.test(o.name))fixed.push(new Box3().setFromObject(o,true));});
  for(const b of open)for(const f of fixed)assert.ok(!b.intersectsBox(f),'open panels clear stationary cabinets/shelves');
  moving.forEach((o,i)=>{const leafWidth={53:.40,54:.56,56:.54,59:.328,60:.40}[spec.id];assert.ok(open[i].max.x-open[i].min.x<leafWidth*.65,'rotated door reduces obstruction at opening');});
 }
 if(spec.id===12){for(let i=0;i<2;i++)assert.ok(open[i].max.y<initial[i].box.max.y-.10,'handles fold down');assert.ok(open[0].max.z>initial[0].box.max.z+.12||open[1].max.z>initial[1].box.max.z+.12,'front handle folds outward');}
 if(spec.id===90)assert.ok(open[0].max.z<-.05,'lid clears central pot opening');
 if(spec.id===95)assert.ok(open.every(b=>b.max.z<-.025),'lids clear tank opening');
 if(spec.id===124){const lower=new Box3().setFromObject(scene.getObjectByName('BODY_Lower'),true);assert.ok(open[0].min.y>lower.max.y+.05,'drawer above lower cabinet');}
 mixer.setTime(2.5);scene.updateMatrixWorld(true);moving.forEach((o,i)=>{assert.ok(o.position.distanceTo(initial[i].p)<.001);assert.ok(o.quaternion.angleTo(initial[i].q)<.001);assert.ok(o.scale.distanceTo(initial[i].s)<.001);});mixer.stopAllAction();
 animationTest='PASS: raw first/last track values and 2.5s duration, intended midpoint motion, measured clearance/opening, LoopOnce final restoration; illustrative movement only';
}else assert.equal(gltf.animations.length,0);
const report={id:spec.title,backlog_id:spec.id,sha256:createHash('sha256').update(bytes).digest('hex'),glb_bytes:bytes.length,triangles,vertices,primitives:Object.keys(parts).length,materials:json.materials.length,textures:0,animations:gltf.animations.length,animationTest,dimensions,bounds:{min:bounds.min.toArray(),max:bounds.max.toArray()},parts,budget,validation:{errors:0,warnings:0,validator:v.validatorVersion},result:'PASS'};
fs.writeFileSync(dir+'reports/assets.json',JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report));

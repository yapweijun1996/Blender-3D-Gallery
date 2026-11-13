import assert from 'node:assert/strict';import fs from 'node:fs';import {fileURLToPath} from 'node:url';import {createHash} from 'node:crypto';import {Box3,Vector3,AnimationMixer,LoopOnce} from 'three';import validator from 'gltf-validator';import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';
const dir=fileURLToPath(new URL('.',import.meta.url)),spec=JSON.parse(fs.readFileSync(dir+'backlog.json')),budget=spec.budget;
const bytes=fs.readFileSync(dir+'exports/optimized.glb'),json=JSON.parse(bytes.subarray(20,20+bytes.readUInt32LE(12)));
const gltf=await new GLTFLoader().parseAsync(bytes.buffer.slice(bytes.byteOffset,bytes.byteOffset+bytes.byteLength),'');const scene=gltf.scene;scene.updateMatrixWorld(true);
const v=await validator.validateBytes(new Uint8Array(bytes));assert.equal(v.issues.numErrors,0);assert.equal(v.issues.numWarnings,0);
const root=scene.getObjectByName(spec.root);assert.ok(root);assert.deepEqual(root.position.toArray(),[0,0,0]);assert.equal(root.userData.units,'metres');assert.ok(json.buffers.every(x=>!x.uri));assert.ok(!json.textures?.length&&!json.images?.length&&!json.cameras?.length&&!json.extensions?.KHR_lights_punctual);
let triangles=0,vertices=0;const parts={};scene.traverse(o=>{if(o.isMesh){const a=o.geometry.attributes.position;assert.ok(o.geometry.attributes.normal);vertices+=a.count;triangles+=(o.geometry.index?.count??a.count)/3;for(const x of a.array)assert.ok(Number.isFinite(x));const b=new Box3().setFromObject(o);parts[o.name]={min:b.min.toArray(),max:b.max.toArray()};}});
assert.ok(bytes.length<=budget.bytes,'fixed byte budget');assert.ok(triangles<=budget.triangles,'fixed polygon budget');assert.ok(Object.keys(parts).length<=budget.mesh_primitives,'fixed mesh primitive budget');assert.ok(Object.keys(parts).length>=4);
const bounds=new Box3().setFromObject(scene,true),dimensions=bounds.getSize(new Vector3()).toArray();
const ranges={29:[[2.69,2.71],[1.33,1.35]],144:[[1.24,1.26],[2.54,2.56]],182:[[.66,.69],[.73,.75]],233:[[1.63,1.65],[1.44,1.46]],89:[[1.24,1.26],[1.28,1.31]],19:[[.65,.67],[1.87,1.89]],112:[[.55,.57],[.99,1.01]],116:[[2.61,2.64],[1.02,1.04]],161:[[8.99,9.01],[.27,.29]],170:[[.29,.31],[.92,.94]],21:[[9.99,10.01],[13.09,13.11]],30:[[3.59,3.61],[2.47,2.49]],41:[[17.99,18.01],[21.99,22.01]],42:[[11.99,12.01],[4.59,4.65]],67:[[20.99,21.01],[6.56,6.60]],181:[[7.99,8.01],[3.19,3.21]]};
for(let i=0;i<2;i++)assert.ok(dimensions[i]>=ranges[spec.id][i][0]&&dimensions[i]<=ranges[spec.id][i][1],spec.id+' dimension '+i+': '+dimensions[i]);
assert.ok(bounds.min.y>=-.01&&bounds.min.y<.011,'metric floor datum/contact');
const required={29:['PANEL_Main','PANEL_Return','CONNECTOR_T','RACEWAY_RemovableCover'],144:['TYRE','MAST_Rail','MOVABLE_Carriage','FORK_Blade'],182:['BOOK_Basket','BAG_HookStem','FRAME_Foot'],233:['WELL_Base','GUARD_ClearPane','MOVABLE_WellLid'],89:['GLASS_Front','DISPLAY_Tray','MOVABLE_RearDoor'],19:['KEYPAD_Keys','CASH_Mouth','CARD_Slot','MOVABLE_ServiceDoor'],112:['WHEEL_Assembly','SPOKES','FRAME_SEAT_Tube','FRONT_Fork','PEDAL'],116:['MOVABLE_Arm','HINGE_Axle','CABINET'],161:['ROAD_Carriageway','SIDEWALK','KERB','ROAD_Markings','DRAIN_Grating'],170:['POST','BASE_Plate','REFLECTIVE_Band','TOP_Cap'],21:['FACADE_Storey','CORE','ENTRY_Canopy','ROOF_PlantRoom'],30:['WALL_Side','WALL_Rear','MOVABLE_Door','CEILING_LightRail'],41:['VOIDDECK_Column','SLAB_Storey','STOREY_FacadeAndCorridor','LIFT_Core','STAIR_Core'],42:['TRANSFER_Main','SERVICE_Core','STAIR_Step','COLUMN'],67:['WING_Slab','WING_Facades','COURTYARD','ARCADE_Column'],181:['WINDOW_Clear','DOOR_Header','MOVABLE_Door','BOARD_MountRail','CABLE_Trunk']};
for(const prefix of required[spec.id])assert.ok((()=>{let found=false;scene.traverse(o=>{if(o.name.startsWith(prefix))o.traverse(c=>{if(c.isMesh)found=true;});});return found;})(),'required real editable component '+prefix);
const matching=prefix=>{const a=[];scene.traverse(o=>{if(o.name.startsWith(prefix))a.push(o);});return a;};
if(spec.id===29){assert.ok(dimensions[2]>1.5&&dimensions[1]<1.4,'low T workstation footprint, not tall folding privacy screen');assert.equal(matching('PANEL_Main').length,2);assert.equal(matching('PANEL_Return').length,1);}
if(spec.id===161){const ends=matching('CONNECT_RoadEnd');assert.equal(ends.length,2);assert.ok(ends.every(o=>o.userData.carriageway_width_m===6.4&&o.userData.module_length_m===10));assert.ok(Math.abs(dimensions[2]-10)<.001);}
if([233,89,30,181].includes(spec.id))assert.ok(json.materials.some(m=>m.alphaMode==='BLEND'&&m.pbrMetallicRoughness.baseColorFactor[3]<.3),'actual standard-alpha glazing');
const counts={144:1,233:2,89:1,19:1,116:1,30:1,181:1};
let animationTest='NOT APPLICABLE: static asset, no fabricated animation';
if(counts[spec.id]){
 assert.equal(gltf.animations.length,counts[spec.id]);const moving=matching('MOVABLE_');assert.equal(moving.length,counts[spec.id]);
 const old=moving.map(o=>({p:o.position.clone(),q:o.quaternion.clone(),s:o.scale.clone()}));const mixer=new AnimationMixer(scene);
 for(const clip of gltf.animations){assert.ok(Math.abs(clip.duration-2.5)<1e-5);for(const t of clip.tracks){const n=t.getValueSize();assert.ok(Math.abs(t.times[0]-1/24)<1e-5);assert.ok(Math.abs(t.times.at(-1)-2.5)<1e-5);for(let k=0;k<n;k++)assert.ok(Math.abs(t.values[k]-t.values[t.values.length-n+k])<1e-5,'raw endpoint equality without loop wrapping');}const action=mixer.clipAction(clip);action.setLoop(LoopOnce,1);action.clampWhenFinished=true;action.play();}
 mixer.setTime(1.25);scene.updateMatrixWorld(true);const open=moving.map(o=>new Box3().setFromObject(o,true));
 moving.forEach((o,i)=>{
  if(spec.id===144)assert.ok(Math.abs(o.position.y-old[i].p.y-1.20)<.001,'carriage rises on mast');
  else if(spec.id===89)assert.ok(Math.abs(o.position.x-old[i].p.x-.56)<.001,'rear pane slides across its parallel track');
  else {assert.ok(Math.abs(o.quaternion.angleTo(old[i].q)-(spec.id===116?1.4:1.3))<.001,'specified hinge angle');assert.ok(o.position.distanceTo(old[i].p)<1e-6,'fixed hinge');}
 });
 if(spec.id===144){assert.ok(open[0].min.y>1.35&&open[0].max.y<2.40,'forks clear floor and carriage stays below mast top');const fixed=matching('CABIN_Post').concat(matching('OVERHEAD_Guard'));for(const o of fixed)assert.ok(!open[0].intersectsBox(new Box3().setFromObject(o,true)),'raised carriage clears cabin');}
 if(spec.id===233)assert.ok(open.every(b=>b.max.z<.10&&b.min.y>.88),'lids move behind well opening and above counter');
 if(spec.id===89){assert.ok(open[0].min.x>-.02&&open[0].max.x<.58,'half-width rear opening with door inside cabinet width');const fixed=new Box3().setFromObject(scene.getObjectByName('REAR_FixedPane'),true);assert.ok(!open[0].intersectsBox(fixed),'parallel glazing tracks do not collide');}
 if(spec.id===19){assert.ok(open[0].max.z<-.275,'service door opens behind cabinet');assert.ok(.275-open[0].max.x>.35,'rear service opening');}
 if(spec.id===116)assert.ok(1.10-open[0].max.x>1.8,'arm clears vehicle passage; pivot intentionally mates with cabinet');
 if(spec.id===30)assert.ok(1.74-open[0].max.x>.60,'meeting room clear opening');
 if(spec.id===181)assert.ok(open[0].min.z-1.60>.70,'classroom doorway clear opening');
 if([30,181].includes(spec.id)){
  const children=new Set();moving.forEach(o=>o.traverse(c=>children.add(c)));scene.traverse(o=>{if(o.isMesh&&!children.has(o)&&/^(WALL_|WINDOW_Pier|DOOR_Header|DOOR_Jamb|FRAME_Post|FLOOR)/.test(o.name))assert.ok(!open[0].intersectsBox(new Box3().setFromObject(o,true)),'open door clears fixed shell');});
 }
 mixer.setTime(2.5);scene.updateMatrixWorld(true);moving.forEach((o,i)=>{assert.ok(o.position.distanceTo(old[i].p)<.001);assert.ok(o.quaternion.angleTo(old[i].q)<.001);assert.ok(o.scale.distanceTo(old[i].s)<.001);});mixer.stopAllAction();
 animationTest='PASS: exact raw exported endpoints and timeline, intended midpoint displacement/angle, measured opening/clearance and LoopOnce restoration; illustrative mechanical motion only';
}else assert.equal(gltf.animations.length,0);
const report={id:spec.title,backlog_id:spec.id,sha256:createHash('sha256').update(bytes).digest('hex'),glb_bytes:bytes.length,triangles,vertices,primitives:Object.keys(parts).length,materials:json.materials.length,textures:0,animations:gltf.animations.length,animationTest,dimensions,bounds:{min:bounds.min.toArray(),max:bounds.max.toArray()},parts,budget,validation:{errors:0,warnings:0,validator:v.validatorVersion},result:'PASS'};
fs.writeFileSync(dir+'reports/assets.json',JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report));

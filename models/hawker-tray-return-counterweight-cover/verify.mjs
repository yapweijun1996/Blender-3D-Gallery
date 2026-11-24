import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {validateBytes} from 'gltf-validator';
import {AnimationMixer,Box3,LoopOnce,Quaternion,Vector3} from 'three';
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';
const slug='hawker-tray-return-counterweight-cover';
const data=await readFile(process.argv[2]??new URL('./exports/'+slug+'.glb',import.meta.url));
const raw=JSON.parse(data.subarray(20,20+data.readUInt32LE(12)));
const kr=await validateBytes(new Uint8Array(data),{uri:slug+'.glb',maxIssues:999});
assert.equal(kr.issues.numErrors,0,JSON.stringify(kr.issues));
assert.equal(kr.issues.numWarnings,0,JSON.stringify(kr.issues));
assert.equal(kr.issues.numInfos,0,JSON.stringify(kr.issues));
assert.deepEqual(raw.buffers.map(b=>b.uri),[undefined]);
assert.equal(raw.images?.length??0,0);
const loaded=await new GLTFLoader().parseAsync(data.buffer.slice(data.byteOffset,data.byteOffset+data.byteLength),'');
const root=loaded.scene;
assert.equal(loaded.animations.length,1);
const [clip]=loaded.animations;
assert.equal(clip.name,'TRAY_RETURN_COVER_LIFT');
assert.ok(Math.abs(clip.duration-2.2)<1e-6);
const names=['TRAY_RETURN_COVER','TRAY_RETURN_COUNTERWEIGHT','TRAY_RETURN_TOP_PULLEY','TRAY_RETURN_COVER_CABLE','TRAY_RETURN_WEIGHT_CABLE','FIXED_ILLUSTRATIVE_SAMPLE_TRAY','FIXED_CONTIGUOUS_TANGENT_HALF_TURN'];
const parts=names.map(s=>root.getObjectByName(s));assert.ok(parts.every(Boolean));
const [cover,weight,pulley,fore,aft,tray,arc]=parts;
const channels=Object.fromEntries(clip.tracks.map(t=>[t.name,t.ValueTypeName]));
assert.deepEqual(channels,{
 'TRAY_RETURN_COUNTERWEIGHT.position':'vector',
 'TRAY_RETURN_COVER.position':'vector',
 'TRAY_RETURN_COVER_CABLE.scale':'vector',
 'TRAY_RETURN_TOP_PULLEY.quaternion':'quaternion',
 'TRAY_RETURN_WEIGHT_CABLE.scale':'vector',
});
for(const t of clip.tracks){assert.equal(t.times[0],0);assert.ok(Math.abs(t.times.at(-1)-2.2)<1e-6);}
const all=(p)=>{const r=[];root.traverse(n=>{if(n.isMesh&&n.name.startsWith(p))r.push(n);});return r;};
const one=p=>{const m=all(p);assert.equal(m.length,1,p);return m[0];};
const b=(n)=>new Box3().setFromObject(n,true);
const foreS=one('Parallel_straight_cable_to_cover'),aftS=one('Parallel_straight_cable_to_counterweight');
const forePin=one('Front_cable_ferrule'),aftPin=one('Rear_cable_ferrule');
const ferruleBound=[forePin,aftPin];
const lips=all('Radiused_inside_guide_lip'),shoes=all('Dark_captured_moving_guide_shoe');
assert.equal(lips.length,4);assert.equal(shoes.length,4);
const guideRods=all('Exposed_round_counterweight_guide_rod');
assert.equal(guideRods.length,2);
const pad=one('Upper_support_pad_outboard'),post=one('Upper_side_return_physically'),side=one('Rear_mechanism_fold_only');
const bridge=one('Cover_link_bridge'),sideLink=one('Cover_side_returned_link');
const weightLips=all('Counterweight_captive_guide_lips'),backTies=all('Counterweight_shoe_back_tie');
assert.equal(weightLips.length,4);assert.equal(backTies.length,2);
const portal=one('Full_receiving_deck');
const movingSkin=one('Solid_stainless_slide_cover');
const globalPos=(n)=>n.getWorldPosition(new Vector3);
const matrixInitial=new Map;
root.updateMatrixWorld(true);
root.traverse(n=>{if(n===tray||n===arc||n===fore||n===aft||n.name.startsWith('FIXED_'))matrixInitial.set(n,n.matrixWorld.clone());});
const mixer=new AnimationMixer(root),motion=mixer.clipAction(clip).setLoop(LoopOnce,1);motion.clampWhenFinished=true;motion.play();
const min={slot:Infinity,rodLips:Infinity,rodTies:Infinity,movingBridgeToGuide:Infinity,rearOfCoverToTray:Infinity,upperPadToWheel:Infinity,shoeScope:Infinity,weightToSide:Infinity};
const max={fixedDrift:0,endAttach:0,topAttach:0,conservedLength:0,oppositeTravel:0};
const sample=[]; let closed=.941, previous=-1, combined;
for(let i=0;i<=132;i++){
 mixer.setTime(i/60);root.updateMatrixWorld(true);
 const cp=globalPos(cover),wp=globalPos(weight);
 const d=cp.y-closed,down=1.407-wp.y;
 assert.ok(d>=previous-1e-7);
 previous=d;
 assert.ok(Math.abs(cp.x)<1e-7&&Math.abs(cp.z)<1e-7);
 assert.ok(Math.abs(wp.x-.623)<1e-7&&Math.abs(wp.z-.159)<1e-7);
 max.oppositeTravel=Math.max(max.oppositeTravel,Math.abs(d-down));
 const ends=[b(foreS),b(aftS)],anchor=[b(forePin),b(aftPin)];
 for(let j=0;j<2;j++){
   const e=ends[j],p=anchor[j],node=[fore,aft][j];
   const ec=e.getCenter(new Vector3),pc=p.getCenter(new Vector3),u=globalPos(node);
   assert.ok(Math.hypot(ec.x-pc.x,ec.z-pc.z)<2e-6);
   max.endAttach=Math.max(max.endAttach,Math.abs(e.min.y-p.max.y));
   max.topAttach=Math.max(max.topAttach,Math.abs(e.max.y-u.y));
 }
 const length=ends[0].max.y-ends[0].min.y+ends[1].max.y-ends[1].min.y;
 if(i===0)combined=length;
 max.conservedLength=Math.max(max.conservedLength,Math.abs(length-combined));
 for(const [n,v] of matrixInitial){
   const actual=n.matrixWorld.elements,old=v.elements;
   if(n===fore||n===aft)max.fixedDrift=Math.max(max.fixedDrift,...[12,13,14].map(k=>Math.abs(actual[k]-old[k])));
   else max.fixedDrift=Math.max(max.fixedDrift,...actual.map((x,k)=>Math.abs(x-old[k])));
 }
 for(const s of shoes) for(const l of lips){
   const a=b(s),f=b(l);
   const xOverlap=Math.min(a.max.x,f.max.x)-Math.max(a.min.x,f.min.x);
   if(xOverlap<0)continue;
   const zgap=Math.max(a.min.z-f.max.z,f.min.z-a.max.z);
   assert.ok(xOverlap>.012&&zgap>.0018, [i,xOverlap,zgap].join(','));
   min.slot=Math.min(min.slot,zgap);
   const margin=Math.min(a.min.y-f.min.y,f.max.y-a.max.y);
   assert.ok(margin>0,[i,margin].join(','));
   min.shoeScope=Math.min(min.shoeScope,margin);
 }
 for(const r of guideRods){
   const f=b(r);
   for(const s of weightLips){
     const a=b(s);
     if(Math.max(a.min.x-f.max.x,f.min.x-a.max.x)>0)continue;
     const g=Math.max(a.min.z-f.max.z,f.min.z-a.max.z);
     assert.ok(g>.00028,[i,g].join(','));
     min.rodLips=Math.min(min.rodLips,g);
   }
   for(const s of backTies){
     const a=b(s),g=Math.max(a.min.x-f.max.x,f.min.x-a.max.x);
     assert.ok(g>.0015,[i,g].join(','));
     min.rodTies=Math.min(min.rodTies,g);
   }
 }
 const bridgeGap=Math.min(...lips.filter(l=>globalPos(l).x>0).map(l=>b(l).min.x-b(bridge).max.x));
 const trayGap=b(movingSkin).min.z-b(tray).max.z;
 const pulleyGap=b(pad).min.x-b(pulley).max.x;
 const sideGap=b(side).min.x-b(weight).max.x;
 assert.ok(bridgeGap>.0042&&trayGap>.0053&&pulleyGap>.010&&sideGap>.0025,JSON.stringify([i,bridgeGap,trayGap,pulleyGap,sideGap]));
 min.movingBridgeToGuide=Math.min(min.movingBridgeToGuide,bridgeGap);
 min.rearOfCoverToTray=Math.min(min.rearOfCoverToTray,trayGap);
 min.upperPadToWheel=Math.min(min.upperPadToWheel,pulleyGap);
 min.weightToSide=Math.min(min.weightToSide,sideGap);
 assert.ok(b(post).intersectsBox(b(side))&&b(post).intersectsBox(b(pad)));
 assert.ok(b(sideLink).intersectsBox(b(bridge)));
 const contact=b(tray).min.y-b(portal).max.y;
 assert.ok(Math.abs(contact)<1e-6);
 const targetQ=new Quaternion().setFromAxisAngle(new Vector3(1,0,0),-d/.055);
 assert.ok(pulley.quaternion.angleTo(targetQ)<.0008);
 if([0,60,112,132].includes(i))sample.push({seconds:i/60,coverY:cp.y,weightY:wp.y,cables:ends.map(e=>e.max.y-e.min.y),pulleyAngle:-d/.055});
}
assert.ok(Object.values(max).every(x=>x<2e-6),JSON.stringify(max));
assert.ok(Math.abs(previous-.335)<1e-6);for(const k of ['coverY','weightY','pulleyAngle'])assert.ok(Math.abs(sample[2][k]-sample[3][k])<2e-8);
assert.ok(sample[2].cables.every((x,i)=>Math.abs(x-sample[3].cables[i])<2e-8));
assert.ok(Math.abs(combined-.617)<2e-6);
const info=kr.info;
console.log(JSON.stringify({sha256:createHash('sha256').update(data).digest('hex'),bytes:data.length,issues:kr.issues,triangles:info.totalTriangleCount,vertices:info.totalVertexCount,drawCalls:info.drawCallCount,meshes:raw.meshes.length,materials:raw.materials.length,clip:clip.name,duration:clip.duration,channels,poses:sample,samples:133,minimumClearanceMetres:min,maximumErrorMetres:max,fixedArcCenterLineMetres:Math.PI*.055,totalDesignCenterLineMetres:combined+Math.PI*.055},null,2));

import assert from 'node:assert/strict';import fs from 'node:fs';import {fileURLToPath} from 'node:url';import {createHash} from 'node:crypto';import {Box3,Vector3,AnimationMixer} from 'three';import validator from 'gltf-validator';import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';
const dir=fileURLToPath(new URL('.',import.meta.url)),spec=JSON.parse(fs.readFileSync(dir+'backlog.json'));
const bytes=fs.readFileSync(dir+'exports/optimized.glb'),json=JSON.parse(bytes.subarray(20,20+bytes.readUInt32LE(12)));
const g=await new GLTFLoader().parseAsync(bytes.buffer.slice(bytes.byteOffset,bytes.byteOffset+bytes.byteLength),'');const scene=g.scene;scene.updateMatrixWorld(true);
const v=await validator.validateBytes(new Uint8Array(bytes));assert.equal(v.issues.numErrors,0);assert.equal(v.issues.numWarnings,0);
const root=scene.getObjectByName(spec.root);assert.ok(root);assert.deepEqual(root.position.toArray(),[0,0,0]);assert.equal(root.userData.units,'metres');assert.ok(json.buffers.every(x=>!x.uri));assert.ok(!json.textures?.length&&!json.images?.length&&!json.cameras?.length&&!json.extensions?.KHR_lights_punctual);
let triangles=0,vertices=0;const parts={};scene.traverse(o=>{if(o.isMesh){const a=o.geometry.attributes.position;assert.ok(o.geometry.attributes.normal);vertices+=a.count;triangles+=(o.geometry.index?.count??a.count)/3;for(const x of a.array)assert.ok(Number.isFinite(x));const b=new Box3().setFromObject(o);parts[o.name]={min:b.min.toArray(),max:b.max.toArray()};}});
const complexity=[343,347,348,349,350].includes(spec.id)?'assembly':'prop',maxTriangles=complexity==='assembly'?22000:16000,maxBytes=complexity==='assembly'?1200000:850000;
assert.ok(bytes.length<maxBytes);assert.ok(triangles<maxTriangles);assert.ok(Object.keys(parts).length>=4);
const bounds=new Box3().setFromObject(scene),dimensions=bounds.getSize(new Vector3()).toArray();
const ranges={342:[[2.59,2.61],[.63,.66]],343:[[4.39,4.41],[2.59,2.61]],344:[[1.79,1.81],[.79,.81]],345:[[.59,.61],[.44,.48]],346:[[2.17,2.21],[1.05,1.10]],347:[[2.29,2.31],[2.29,2.31]],348:[[4.39,4.41],[3.09,3.11]],349:[[5.49,5.51],[3.02,3.05]],350:[[5.79,5.81],[3.19,3.22]],351:[[2.18,2.20],[1.07,1.09]],352:[[1.99,2.01],[.85,.87]],353:[[.64,.66],[3.09,3.11]],354:[[.74,.76],[1.19,1.21]],355:[[.27,.29],[1.29,1.31]],356:[[.48,.51],[1.15,1.18]],357:[[.899,.901],[2.21,2.23]],358:[[2.79,2.81],[2.19,2.21]],359:[[1.99,2.01],[.94,.98]]};
for(let i=0;i<2;i++)assert.ok(dimensions[i]>=ranges[spec.id][i][0]&&dimensions[i]<=ranges[spec.id][i][1],`${spec.id} dimension ${i}: ${dimensions[i]}`);
const count=p=>Object.keys(parts).filter(n=>n.startsWith(p)).length;
if(spec.id===351){assert.equal(count('RAIL_Horizontal'),2);assert.equal(count('RAIL_Post'),2);}
if(spec.id===346)assert.equal(count('SEAT_Pan'),3);
if(spec.id===359){assert.equal(count('SEAT_Slat'),4);assert.equal(count('BACK_Slat'),3);}
let animationTest='NOT APPLICABLE';
if([343,345,347].includes(spec.id)){
 assert.ok(g.animations.length>0);const moving=[];scene.traverse(o=>{if(o.name.startsWith('MOVABLE_'))moving.push(o)});assert.ok(moving.length);

 const before=moving.map(o=>({o,position:o.position.clone(),quaternion:o.quaternion.clone(),bounds:new Box3().setFromObject(o)}));
 const mixer=new AnimationMixer(scene);for(const clip of g.animations){assert.ok(Math.abs(clip.duration-60/24)<.002);mixer.clipAction(clip).play();}
 mixer.setTime(30/24);scene.updateMatrixWorld(true);
 if(spec.id===345){
  assert.equal(moving.length,1);assert.ok(Math.abs(before[0].quaternion.angleTo(moving[0].quaternion)-.3)<.002,'handle swing 0.3rad');
  assert.ok(moving[0].position.distanceTo(before[0].position)<1e-6,'hinge location unchanged');
 }else{
  assert.equal(moving.length,2);const expected=spec.id===343?1.05:.9,open=[];
  for(const b of before){
   const left=b.bounds.getCenter(new Vector3()).x<0;const dx=b.o.position.x-b.position.x;
   assert.ok(Math.abs(dx-(left?-expected:expected))<.002,'opposing exact travel');
   assert.ok(Math.abs(b.o.position.y-b.position.y)<1e-6&&Math.abs(b.o.position.z-b.position.z)<1e-6,'no vertical/depth drift');
   open.push(new Box3().setFromObject(b.o));
  }
  open.sort((a,b)=>a.min.x-b.min.x);assert.ok(open[1].min.x-open[0].max.x>(spec.id===343?2.09:1.80),'clear aperture at full opening');
  // No open leaf may intersect the stationary jamb/post volumes.
  const fixed=[];scene.traverse(o=>{if(o.isMesh&&(o.name.startsWith('FRAME_Post')||o.name.startsWith('FRAME_Side')))fixed.push(new Box3().setFromObject(o));});
  for(const door of open)for(const post of fixed)assert.ok(!door.intersectsBox(post),'open leaf clears fixed jamb');
 }
 mixer.setTime(60/24-.00001);scene.updateMatrixWorld(true);
 for(const b of before){assert.ok(b.o.position.distanceTo(b.position)<.002,'returns to closed/rest position');assert.ok(b.o.quaternion.angleTo(b.quaternion)<.002,'returns to rest rotation');}
 mixer.stopAllAction();animationTest='PASS: duration 60/24s; midpoint intended travel/swing; door clear aperture and fixed-jamb clearance; end restoration';
}else assert.equal(g.animations.length,0);
const report={id:spec.title,backlog_id:spec.id,sha256:createHash('sha256').update(bytes).digest('hex'),glb_bytes:bytes.length,triangles,vertices,primitives:Object.keys(parts).length,materials:json.materials.length,textures:0,animations:g.animations.length,animationTest,dimensions,bounds:{min:bounds.min.toArray(),max:bounds.max.toArray()},parts,validation:{errors:0,warnings:0,validator:v.validatorVersion},budget:{complexity,triangles:maxTriangles,bytes:maxBytes},result:'PASS'};
fs.writeFileSync(dir+'reports/assets.json',JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report));

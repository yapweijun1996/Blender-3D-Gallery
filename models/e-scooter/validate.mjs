import assert from 'node:assert/strict';import fs from 'node:fs';import {fileURLToPath} from 'node:url';import {createHash} from 'node:crypto';import {Box3,Vector3,AnimationMixer,LoopOnce} from 'three';import validator from 'gltf-validator';import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';
const dir=fileURLToPath(new URL('.',import.meta.url)),s=JSON.parse(fs.readFileSync(dir+'backlog.json')),bytes=fs.readFileSync(dir+'exports/optimized.glb'),json=JSON.parse(bytes.subarray(20,20+bytes.readUInt32LE(12)));
const g=await new GLTFLoader().parseAsync(bytes.buffer.slice(bytes.byteOffset,bytes.byteOffset+bytes.byteLength),'');g.scene.updateMatrixWorld(true);
const v=await validator.validateBytes(new Uint8Array(bytes));assert.equal(v.issues.numErrors,0);assert.equal(v.issues.numWarnings,0);assert.ok(json.buffers.every(b=>!b.uri));assert.ok(!json.images?.length&&!json.textures?.length&&!json.cameras?.length&&!json.extensions?.KHR_lights_punctual);
const root=g.scene.getObjectByName(s.root);assert.ok(root);assert.deepEqual(root.position.toArray(),[0,0,0]);assert.equal(root.userData.units,'metres');
let triangles=0;const parts={};g.scene.traverse(o=>{if(o.isMesh){assert.ok(o.geometry.attributes.normal);assert.ok([...o.geometry.attributes.position.array].every(Number.isFinite));triangles+=(o.geometry.index?.count??o.geometry.attributes.position.count)/3;const b=new Box3().setFromObject(o,true);parts[o.name]={min:b.min.toArray(),max:b.max.toArray()};}});
const b=new Box3().setFromObject(g.scene,true),dims=b.getSize(new Vector3()).toArray(),expected=[s.dimensions[0],s.dimensions[2],s.dimensions[1]];
for(let i=0;i<3;i++)assert.ok(dims[i]>=expected[i]*.74&&dims[i]<=expected[i]*1.26,'metre envelope axis'+i+':'+dims[i]);
assert.ok(Math.abs(b.min.y)<.012,'ground datum');assert.ok(bytes.length<=s.budget.bytes,'fixed byte budget');assert.ok(triangles<=s.budget.triangles,'fixed triangle budget');assert.ok(Object.keys(parts).length<=s.budget.mesh_primitives);assert.ok(Object.keys(parts).length>=4);
for(const prefix of s.features)assert.ok(Object.keys(parts).some(n=>n.startsWith(prefix)),'required editable feature '+prefix);
const anim=s.animation;let animationTest='STATIC: zero fabricated clips';
if(anim){
 assert.equal(g.animations.length,1);const moving=g.scene.getObjectByName(anim.node);assert.ok(moving);
 const p=moving.position.clone(),q=moving.quaternion.clone(),closed=new Box3().setFromObject(moving,true);
 for(const clip of g.animations){assert.ok(Math.abs(clip.duration-2.5)<1e-5);for(const track of clip.tracks){assert.ok(Math.abs(track.times[0]-1/24)<1e-5);assert.ok(Math.abs(track.times.at(-1)-2.5)<1e-5);const n=track.getValueSize();for(let i=0;i<n;i++)assert.ok(Math.abs(track.values[i]-track.values[track.values.length-n+i])<1e-5,'raw cyclic endpoints');}}
 const mixer=new AnimationMixer(g.scene);for(const clip of g.animations){const a=mixer.clipAction(clip);a.setLoop(LoopOnce,1);a.clampWhenFinished=true;a.play();}mixer.setTime(1.25);g.scene.updateMatrixWorld(true);
 const open=new Box3().setFromObject(moving,true);
 if(anim.kind==='rotation'){assert.ok(Math.abs(q.angleTo(moving.quaternion)-anim.angle)<.001,'hinge angle');assert.ok(p.distanceTo(moving.position)<1e-6,'fixed pivot');}
 else {assert.ok(Math.abs(moving.position.getComponent(anim.axis)-p.getComponent(anim.axis)-anim.travel)<.001,'travel');for(let i=0;i<3;i++)if(i!==anim.axis)assert.ok(Math.abs(moving.position.getComponent(i)-p.getComponent(i))<1e-6);}
 if(s.id===39){assert.ok(open.min.y>.34,'tripod arm floor clearance');assert.ok(open.min.x>.17,'arms clear cabinet shell');}
 if(s.id===131){assert.ok(open.max.x-moving.position.x<.36,'door opens away from aperture');assert.ok(open.min.y>.17&&open.max.y<1.73,'door clears plinth and header');}
 if(s.id===114){assert.ok(open.min.x>-1.16&&open.max.x<-.42,'flap fully retracted into left cabinet footprint');assert.ok(open.min.y>.30,'flap floor clearance');}
 if(s.id===147){assert.ok(open.min.y>1.10,'leveller clears dock face height');assert.ok(open.min.x>-.94&&open.max.x<.94,'leveller clears bumpers');}
 mixer.setTime(2.5);g.scene.updateMatrixWorld(true);assert.ok(moving.position.distanceTo(p)<1e-5&&moving.quaternion.angleTo(q)<.001,'restoration');mixer.stopAllAction();animationTest='PASS raw endpoints, intended Mixer midpoint, geometric clearance and restoration';
}else assert.equal(g.animations.length,0);
const report={result:'PASS',id:s.slug,backlog_id:s.id,glb_bytes:bytes.length,triangles,primitives:Object.keys(parts).length,materials:json.materials.length,dimensions:dims,bounds:{min:b.min.toArray(),max:b.max.toArray()},sha256:createHash('sha256').update(bytes).digest('hex'),budget:s.budget,animationTest,animations:g.animations.length,validation:{errors:0,warnings:0},parts};fs.writeFileSync(dir+'reports/assets.json',JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report));

import assert from 'node:assert/strict';import fs from 'node:fs';import {fileURLToPath} from 'node:url';import {createHash} from 'node:crypto';import {Box3,Vector3,AnimationMixer,LoopOnce} from 'three';import validator from 'gltf-validator';import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';
const dir=fileURLToPath(new URL('.',import.meta.url)),s=JSON.parse(fs.readFileSync(dir+'backlog.json')),a=s.animation,bytes=fs.readFileSync(dir+'exports/optimized.glb'),json=JSON.parse(bytes.subarray(20,20+bytes.readUInt32LE(12)));
const g=await new GLTFLoader().parseAsync(bytes.buffer.slice(bytes.byteOffset,bytes.byteOffset+bytes.byteLength),'');g.scene.updateMatrixWorld(true);
const v=await validator.validateBytes(new Uint8Array(bytes));assert.equal(v.issues.numErrors,0);assert.equal(v.issues.numWarnings,0);assert.ok(json.buffers.every(b=>!b.uri));assert.ok(!json.images?.length&&!json.textures?.length&&!json.cameras?.length&&!json.extensions?.KHR_lights_punctual);
const root=g.scene.getObjectByName(s.root);assert.ok(root);assert.deepEqual(root.position.toArray(),[0,0,0]);assert.equal(root.userData.units,'metres');
const find=prefix=>{const x=[];root.traverse(o=>{if(o.name.startsWith(prefix))x.push(o);});return x;};
let triangles=0;const parts={};root.traverse(o=>{if(o.isMesh){assert.ok(o.geometry.attributes.normal);assert.ok([...o.geometry.attributes.position.array].every(Number.isFinite));triangles+=(o.geometry.index?.count??o.geometry.attributes.position.count)/3;const b=new Box3().setFromObject(o,true);parts[o.name]={min:b.min.toArray(),max:b.max.toArray()};}});
const bounds=new Box3().setFromObject(root,true),dims=bounds.getSize(new Vector3()).toArray(),expected=[s.dimensions[0],s.dimensions[2],s.dimensions[1]];
for(let i=0;i<3;i++)assert.ok(dims[i]>=expected[i]*.85&&dims[i]<=expected[i]*1.15,'fixed vehicle metre envelope axis'+i+':'+dims[i]);
assert.ok(Math.abs(bounds.min.y)<.001,'tyre ground datum');assert.ok(bytes.length<=s.budget.bytes);assert.ok(triangles<=s.budget.triangles);assert.ok(Object.keys(parts).length<=s.budget.mesh_primitives);
for(const prefix of s.features)assert.ok(Object.keys(parts).some(n=>n.startsWith(prefix)),prefix);
const tyres=find('TYRE'),rolls=find('ROLL_Wheel'),steers=find('STEER_Front'),doors=a.doors.map(d=>{const o=root.getObjectByName(d.node);assert.ok(o);return {o,spec:d};});
assert.equal(tyres.length,4);assert.equal(rolls.length,4);assert.equal(steers.length,2);assert.equal(g.animations.length,6+doors.length);
assert.equal(root.userData.wheel_radius_m,a.wheel_radius);assert.equal(root.userData.wheel_track_m,a.track);assert.ok(Math.abs(root.userData.wheelbase_m-(a.axles[1]-a.axles[0]))<1e-6);
const initial=new Map([...rolls,...steers,...doors.map(d=>d.o)].map(o=>[o,{p:o.position.clone(),q:o.quaternion.clone(),scale:o.scale.clone()}]));
for(const tyre of tyres){const c=tyre.getWorldPosition(new Vector3()),b=new Box3().setFromObject(tyre,true);assert.ok(Math.abs(Math.abs(c.x)-a.track/2)<1e-5);assert.ok(a.axles.some(y=>Math.abs(c.z+y)<1e-5));assert.ok(Math.abs(c.y-a.wheel_radius)<1e-5);assert.ok(Math.abs((b.max.y-b.min.y)/2-a.wheel_radius)<.001);assert.ok(Math.abs(b.max.x-b.min.x-.24)<.001);}
for(const clip of g.animations){assert.ok(Math.abs(clip.duration-2.5)<1e-5);for(const t of clip.tracks){assert.ok(Math.abs(t.times[0]-1/24)<1e-5&&Math.abs(t.times.at(-1)-2.5)<1e-5);const n=t.getValueSize();for(let i=0;i<n;i++)assert.ok(Math.abs(t.values[i]-t.values[t.values.length-n+i])<1e-5,'raw endpoint restoration');}}
const mixer=new AnimationMixer(g.scene),play=()=>{mixer.stopAllAction();for(const clip of g.animations){const action=mixer.clipAction(clip);action.reset();action.setLoop(LoopOnce,1);action.clampWhenFinished=true;action.play();}};
const fixed=[];root.traverse(o=>{if(!o.isMesh)return;let p=o,moving=false;while(p&&p!==root){if(/^(MOVABLE|ROLL|STEER)/.test(p.name))moving=true;p=p.parent;}if(!moving)fixed.push(o);});
const overlap=(b,c)=>[Math.min(b.max.x,c.max.x)-Math.max(b.min.x,c.min.x),Math.min(b.max.y,c.max.y)-Math.max(b.min.y,c.min.y),Math.min(b.max.z,c.max.z)-Math.max(b.min.z,c.min.z)];
play();let maxContactError=0;
for(let frame=1;frame<=60;frame++){
 mixer.setTime(frame/24);g.scene.updateMatrixWorld(true);
 for(const tyre of tyres){const b=new Box3().setFromObject(tyre,true),err=Math.abs(b.min.y);maxContactError=Math.max(maxContactError,err);assert.ok(err<.003,'polygon tyre contact '+frame);for(const f of fixed)assert.ok(overlap(b,new Box3().setFromObject(f,true)).some(x=>x<=.0001),'tyre/body clearance '+frame+' '+tyre.name+' '+f.name);}
 for(const {o}of doors){const b=new Box3().setFromObject(o,true);for(const f of fixed)assert.ok(overlap(b,new Box3().setFromObject(f,true)).some(x=>x<=.0001),'door/fixed sweep '+frame+' '+o.name+' '+f.name);}
 for(let i=0;i<doors.length;i++)for(let j=i+1;j<doors.length;j++)assert.ok(overlap(new Box3().setFromObject(doors[i].o,true),new Box3().setFromObject(doors[j].o,true)).some(x=>x<=.0001),'door pair sweep '+frame);
}
play();mixer.setTime(1.25);g.scene.updateMatrixWorld(true);
for(const r of rolls)assert.ok(Math.abs(r.quaternion.angleTo(initial.get(r).q)-Math.PI)<1e-4,'half-turn roll');
for(const r of steers)assert.ok(Math.abs(r.quaternion.angleTo(initial.get(r).q)-.22)<1e-4,'steering angle');
for(const {o,spec:d} of doors){const init=initial.get(o);if(d.kind==='rotation'){assert.ok(Math.abs(o.quaternion.angleTo(init.q)-d.angle)<1e-4);assert.ok(o.position.distanceTo(init.p)<1e-5);}else assert.ok(Math.abs(o.position.getComponent(d.axis)-init.p.getComponent(d.axis)-d.travel)<1e-4);}
mixer.setTime(2.5);g.scene.updateMatrixWorld(true);for(const [o,b]of initial){assert.ok(o.position.distanceTo(b.p)<1e-5&&o.quaternion.angleTo(b.q)<1e-4&&o.scale.distanceTo(b.scale)<1e-5);}mixer.stopAllAction();
const report={result:'PASS',id:s.slug,backlog_id:s.id,sha256:createHash('sha256').update(bytes).digest('hex'),glb_bytes:bytes.length,triangles,primitives:Object.keys(parts).length,materials:json.materials.length,dimensions:dims,bounds:{min:bounds.min.toArray(),max:bounds.max.toArray()},budget:s.budget,animations:g.animations.length,animationTest:'60-frame actual tire contact, tire/body, door/fixed and door-pair AABB clearance; exact axles/radius/track; raw endpoints, midpoint half-turn/steer/door and restoration. Not full wheel spin or driving physics.',maxContactError,validation:{errors:0,warnings:0},parts};fs.writeFileSync(dir+'reports/assets.json',JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report));

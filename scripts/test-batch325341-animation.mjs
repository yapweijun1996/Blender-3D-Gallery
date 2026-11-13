import fs from 'node:fs';import assert from 'node:assert/strict';import {pathToFileURL,fileURLToPath} from 'node:url';
const R=fileURLToPath(new URL('../',import.meta.url));
const {GLTFLoader}=await import(pathToFileURL(R+'node_modules/three/examples/jsm/loaders/GLTFLoader.js'));const {AnimationMixer,Box3}=await import(pathToFileURL(R+'node_modules/three/build/three.module.js'));
for(const s of JSON.parse(fs.readFileSync(R+'scripts/batch325341.json')).filter(x=>x.animation_nodes)){
 const p=R+'models/'+s.slug+'/',bytes=fs.readFileSync(p+'exports/'+s.slug+'.glb'),g=await new GLTFLoader().parseAsync(bytes.buffer.slice(bytes.byteOffset,bytes.byteOffset+bytes.byteLength),'');
 const mixer=new AnimationMixer(g.scene);for(const c of g.animations)mixer.clipAction(c).play();const start=Math.min(...g.animations.flatMap(c=>c.tracks.map(t=>t.times[0]))),end=Math.max(...g.animations.map(c=>c.duration));assert.ok(Math.abs((end-start)-2)<1e-5);mixer.setTime(start);
 const pose=()=>s.animation_nodes.map(n=>{const o=g.scene.getObjectByName(n);assert.ok(o);return {name:n,position:o.position.toArray(),quaternion:o.quaternion.toArray()};});
 const expected={
325:[{p:[0,0,0],q:[0,0,0,1],openP:[3.25,0,0],openQ:[0,0,0,1]}],
328:[{p:[0,1.445,0],q:[0,0,0,1],openP:[0,1.745,0],openQ:[0,0,0,1]}],
329:[{p:[-.21,.30,.15],q:[0,0,0,1],openP:[-.21,.30,.15],openQ:[0,-Math.sin(.65),0,Math.cos(.65)]}],
330:[{p:[-.30,.55,.20],q:[0,0,0,1],openP:[-.30,.55,.20],openQ:[0,-Math.sin(.65),0,Math.cos(.65)]}],
335:[{p:[-.53,.65,.055],q:[0,0,0,1],openP:[-.53,.65,.055],openQ:[0,-Math.sin(.65),0,Math.cos(.65)]},{p:[.53,.65,.055],q:[0,0,0,1],openP:[.53,.65,.055],openQ:[0,Math.sin(.65),0,Math.cos(.65)]}],
338:[{p:[-.25,.90,.59],q:[0,0,0,1],openP:[-.25,.90,.59],openQ:[0,-Math.sin(.65),0,Math.cos(.65)]}]
}[s.id];
const closeTo=(a,b)=>{assert.equal(a.length,b.length);a.forEach((x,i)=>assert.ok(Math.abs(x-b[i])<1e-5,'expected '+b[i]+' got '+x));};
const staticNodes=[];g.scene.traverse(o=>{if(!s.animation_nodes.includes(o.name))staticNodes.push({o,p:o.position.toArray(),q:o.quaternion.toArray()});});
const closed=pose();closed.forEach((v,i)=>{closeTo(v.position,expected[i].p);closeTo(v.quaternion,expected[i].q);});mixer.setTime((start+end)/2);const open=pose();assert.notDeepEqual(open,closed);open.forEach((v,i)=>{closeTo(v.position,expected[i].openP);closeTo(v.quaternion,expected[i].openQ);});
for(const v of staticNodes){closeTo(v.o.position.toArray(),v.p);closeTo(v.o.quaternion.toArray(),v.q);}
if(s.id===325){g.scene.updateMatrixWorld(true);const leaf=new Box3().setFromObject(g.scene.getObjectByName('MOVABLE_Sliding_Leaf'));const track=new Box3().setFromObject(g.scene.getObjectByName('Ground_Track'));assert.ok(leaf.min.z>.15,'gate clears post front plane');assert.ok(leaf.max.x<track.max.x,'open gate stays over track');}
mixer.setTime(end);const reset=pose();
 for(let i=0;i<closed.length;i++)for(const prop of ['position','quaternion'])for(let j=0;j<closed[i][prop].length;j++)assert.ok(Math.abs(closed[i][prop][j]-reset[i][prop][j])<1e-5);
 const report={result:'PASS',sample_times:{closed:start,open:(start+end)/2,reset:end},clips:g.animations.map(c=>({name:c.name,duration:c.duration,tracks:c.tracks.length})),closed,open,reset,expected_poses:expected,fixed_components_unchanged:true,verification:'Three.js AnimationMixer closed-open-closed transforms; Gallery controls not implemented'};
 fs.writeFileSync(p+'reports/animation.json',JSON.stringify(report,null,2)+'\n');console.log('ANIMATION_PASS',s.id,g.animations.length);
}

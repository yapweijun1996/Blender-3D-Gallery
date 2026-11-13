import assert from 'node:assert/strict';
import fs from 'node:fs';
import {AnimationMixer,LoopOnce,Box3} from 'three';
import {readGlb} from './glb.mjs';
const root=new URL('.',import.meta.url),{scene,animations}=await readGlb(new URL('exports/optimized.glb',root));
assert.equal(animations.length,2);
for(const c of animations)for(const t of c.tracks){assert.equal(t.times[0],0);assert.equal(t.times[t.times.length-1],2);const n=t.getValueSize();for(let i=0;i<n;i++)assert.ok(Math.abs(t.values[i]-t.values[t.values.length-n+i])<1e-6,'track endpoints match without repeat wrapping');}

const leaves=['MOVABLE_LeftLeaf','MOVABLE_RightLeaf'].map(n=>scene.getObjectByName(n));
assert.ok(leaves.every(Boolean));
const rests=leaves.map(o=>({position:o.position.clone(),q:o.quaternion.clone()}));
const mixer=new AnimationMixer(scene);
for(const clip of animations){assert.ok(Math.abs(clip.duration-2)<.01);const action=mixer.clipAction(clip);action.setLoop(LoopOnce,1);action.clampWhenFinished=true;action.play();}
mixer.setTime(1);scene.updateMatrixWorld(true);
const angles=leaves.map((o,i)=>o.quaternion.angleTo(rests[i].q));
for(let i=0;i<leaves.length;i++){assert.ok(Math.abs(angles[i]-70*Math.PI/180)<.005);assert.ok(leaves[i].position.distanceTo(rests[i].position)<1e-6);}
const leftBox=new Box3().setFromObject(leaves[0]),rightBox=new Box3().setFromObject(leaves[1]);
assert.ok(leftBox.max.x<rightBox.min.x,'open leaves must clear central entry');
mixer.setTime(2);scene.updateMatrixWorld(true);
for(let i=0;i<leaves.length;i++)assert.ok(leaves[i].quaternion.angleTo(rests[i].q)<.001);
mixer.stopAllAction();
const report={result:'PASS',runtime:'Three.js AnimationMixer on actual parsed GLB',clips:animations.map(x=>({name:x.name,duration:x.duration})),openAnglesRadians:angles,hingePositionsUnchanged:true,centralEntryClearWhenOpen:true,restoredClosed:true,galleryPlaybackUI:'NOT IMPLEMENTED'};
fs.writeFileSync(new URL('reports/animation-proof.json',root),JSON.stringify(report,null,2)+'\n');console.log('PASS synchronized gate animation');

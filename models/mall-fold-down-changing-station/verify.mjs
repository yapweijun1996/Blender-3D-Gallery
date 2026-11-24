import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {validateBytes} from 'gltf-validator';
import {AnimationMixer, QuaternionKeyframeTrack, Vector3} from 'three';
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';
const id='mall-fold-down-changing-station';
const bin=await readFile(new URL('./exports/'+id+'.glb',import.meta.url));
const check=await validateBytes(new Uint8Array(bin),{uri:id+'.glb',maxIssues:1000});
assert.deepEqual([check.issues.numErrors,check.issues.numWarnings,check.issues.numInfos],[0,0,0],JSON.stringify(check.issues));
const j=JSON.parse(bin.subarray(20,20+bin.readUInt32LE(12)));
assert.equal(j.asset.version,'2.0');
assert.deepEqual(j.buffers.map(x=>x.uri),[undefined]);
assert.equal(j.images?.length??0,0);assert.equal(j.textures?.length??0,0);assert.equal(j.animations.length,1);
const {scene,animations}=await new GLTFLoader().parseAsync(bin.buffer.slice(bin.byteOffset,bin.byteOffset+bin.byteLength),'');
const [clip]=animations;
assert.equal(clip.name,'CHANGING_STATION_UNFOLD');assert.ok(Math.abs(clip.duration-2.20)<1e-6);
assert.equal(clip.tracks.length,1);
const [track]=clip.tracks;assert.ok(track instanceof QuaternionKeyframeTrack);
assert.equal(track.name,'CHANGING_DECK_HINGE.quaternion');
const requireName=name=>{const o=scene.getObjectByName(name);assert.ok(o,name);return o;};
const pivot=requireName('CHANGING_DECK_HINGE');
const context=requireName('FAMILY_ROOM_DISPLAY_CONTEXT');
const body=requireName('CHANGING_STATION_HOUSING');
const stationary=[];for(const root of [context,body])root.traverse(n=>stationary.push(n));
scene.updateMatrixWorld(true);
const original=stationary.map(o=>[...o.matrixWorld.elements]);
const mixer=new AnimationMixer(scene);const action=mixer.clipAction(clip).play();
const P=new Vector3(0,.851,.124);
const poses=[];let old=90.001;
for(let i=0;i<=132;i++){
  const t=Math.min(i/60,clip.duration-0.0000001);
  mixer.setTime(t);scene.updateMatrixWorld(true);
  assert.ok(pivot.getWorldPosition(new Vector3()).distanceTo(P)<1e-6);
  const direction=new Vector3(0,0,1).applyMatrix4(pivot.matrixWorld).sub(P).normalize();
  const up=new Vector3(0,1,0).transformDirection(pivot.matrixWorld);
  assert.ok(Math.abs(direction.x)<1e-6);assert.ok(Math.abs(up.x)<1e-6);
  const angle=Math.atan2(direction.y,direction.z)*180/Math.PI;
  assert.ok(angle<=old+0.00001);old=angle;
  if(i>=112){assert.ok(Math.abs(angle)<1e-5);assert.ok(up.distanceTo(new Vector3(0,1,0))<1e-6);}
  for(const [i,o] of stationary.entries())assert.deepEqual(o.matrixWorld.elements,original[i]);
  if([0,33,66,99,116,132].includes(i))poses.push({seconds:t,angle});
}
assert.ok(Math.abs(poses[0].angle-90)<.00002);
const info=check.info;
console.log(JSON.stringify({glb_sha256:createHash('sha256').update(bin).digest('hex'),glb_bytes:bin.length,
  triangles:info.totalTriangleCount,vertices:info.totalVertexCount,draw_calls:info.drawCallCount,
  meshes:j.meshes.length,materials:j.materials.length,animations:animations.length,maximum_texture_dimension_px:0,
  khronos:check.issues,clip:clip.name,clip_seconds:clip.duration,track:track.name,raw_interpolation:j.animations[0].samplers[0].interpolation,stationary_objects:stationary.length,poses},null,2));

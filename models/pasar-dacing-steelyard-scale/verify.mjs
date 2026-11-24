import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {validateBytes} from 'gltf-validator';
import {AnimationMixer, Box3, LoopOnce, Matrix4, Vector3} from 'three';
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';

const slug='pasar-dacing-steelyard-scale';
const path=new URL('./exports/'+slug+'.glb',import.meta.url);
const data=await readFile(path);
const Khronos=await validateBytes(new Uint8Array(data),{uri:slug+'.glb',maxIssues:1000});
assert.equal(Khronos.issues.numErrors,0,JSON.stringify(Khronos.issues));
assert.equal(Khronos.issues.numWarnings,0,JSON.stringify(Khronos.issues));
const json=JSON.parse(data.subarray(20,20+data.readUInt32LE(12)));
assert.equal(json.asset.version,'2.0');
assert.deepEqual(json.buffers.map(b=>b.uri),[undefined]);
assert.equal(json.images?.length??0,0);
assert.equal(json.textures?.length??0,0);
assert.equal(json.animations.length,1);
const info=Khronos.info;
const loaded=await new GLTFLoader().parseAsync(data.buffer.slice(data.byteOffset,data.byteOffset+data.byteLength),'');
const root=loaded.scene;const [motion]=loaded.animations;
assert.equal(loaded.animations.length,1);
assert.equal(motion.name,'DACING_FIND_BALANCE');
assert.ok(Math.abs(motion.duration-2.2)<1e-6);
const types=Object.fromEntries(motion.tracks.map(t=>[t.name,t.ValueTypeName]));
assert.deepEqual(types,{
  'DACING_BEAM.quaternion':'quaternion',
  'DACING_COUNTERWEIGHT.position':'vector',
  'DACING_PAN_SWIVEL.quaternion':'quaternion',
  'DACING_POISE_SWIVEL.quaternion':'quaternion',
});
const names=['DACING_BEAM','DACING_COUNTERWEIGHT','DACING_PAN_SWIVEL','DACING_POISE_SWIVEL','DACING_SAMPLE_MANGOES','DACING_FIXED_FULCRUM_PIN'];
const [beam,slider,pan,poise,sample,fixed]=names.map(k=>root.getObjectByName(k));
assert.ok(names.every(k=>root.getObjectByName(k)));
assert.equal(slider.parent,beam);assert.equal(pan.parent,beam);assert.equal(poise.parent,slider);assert.equal(sample.parent,pan);
const meshesFor=p=>{const dst=[];root.traverse(n=>{if(n.isMesh&&n.name.startsWith(p))dst.push(n);});return dst;};
const mesh=p=>{const m=meshesFor(p);assert.equal(m.length,1,p);return m[0];};
const ticks=meshesFor('Unitless_ruled_tick'),sideWalls=meshesFor('Open_sliding_collar_side_wall');
const lips=meshesFor('Open_sliding_collar_upperlower_lip');
assert.equal(ticks.length,23); assert.equal(sideWalls.length,2); assert.equal(lips.length,2);
const shaft=mesh('Long_asymmetrical_steelyard_beam');
const rail=mesh('Inlaid_front_face_for_illustrative_ticks');
const stand=mesh('Rear_support_upright');
const tray=mesh('Spun_brass_hanging_produce_pan');
const ground=mesh('Solid_oiled_display_base');
const animator=new AnimationMixer(root),act=animator.clipAction(motion).setLoop(LoopOnce,1);act.clampWhenFinished=true;act.play();
const V=()=>new Vector3();
const wp=n=>n.getWorldPosition(V());
const limits=(objs,axis)=>{
  const inv=new Matrix4().copy(beam.matrixWorld).invert();
  let lo=Infinity,hi=-Infinity;
  for(const ob of objs){
    const vs=ob.geometry.getAttribute('position');
    const mat=inv.clone().multiply(ob.matrixWorld);
    for(let i=0;i<vs.count;i++){
      const n=V().fromBufferAttribute(vs,i).applyMatrix4(mat)[axis];
      lo=Math.min(lo,n);hi=Math.max(hi,n);
    }
  }
  return [lo,hi];
};
let minSlide=Infinity,minGround=Infinity,minStand=Infinity,maxCenter=0,maxUp=0,old=.126-1e-6;
const poses=[];
for(let i=0;i<=132;i++){
  animator.setTime(i/60);
  root.updateMatrixWorld(true);
  const weightLocal=beam.worldToLocal(wp(slider)),pivot=beam.worldToLocal(wp(fixed)),panPivot=beam.worldToLocal(wp(pan));
  assert.ok(weightLocal.x>=old-2e-7);old=weightLocal.x;
  const err=Math.max(Math.hypot(weightLocal.y,weightLocal.z),pivot.length(),panPivot.distanceTo(new Vector3(-.198,-.007,0)));
  maxCenter=Math.max(maxCenter,err);assert.ok(err<2e-6);
  for(const n of [pan,poise]){
    const up=V().setFromMatrixColumn(n.matrixWorld,1);
    const err=up.distanceTo(new Vector3(0,1,0));maxUp=Math.max(maxUp,err);
    assert.ok(err<1e-6);
  }
  assert.ok(sample.position.distanceTo(new Vector3(0,-.303,0))<1e-6);
  assert.ok(wp(fixed).distanceTo(new Vector3(0,.846,0))<1e-6);
  const sorted=(objs,ax)=>[...objs].sort((a,b)=>beam.worldToLocal(wp(a))[ax]-beam.worldToLocal(wp(b))[ax]);
  const close=ticks.filter(t=>Math.abs(beam.worldToLocal(wp(t)).x-weightLocal.x)<.022);
  const envelope=[shaft,rail,...close];
  for(const [obs,axis] of [[sideWalls,'z'],[lips,'y']]){
    const [low,high]=sorted(obs,axis);
    const [lo,hi]=limits(envelope,axis);
    const gap=Math.min(lo-limits([low],axis)[1],limits([high],axis)[0]-hi);
    assert.ok(gap>.00084,JSON.stringify([i,axis,gap]));
    minSlide=Math.min(minSlide,gap);
  }
  const pbox=new Box3().setFromObject(tray,true),b=new Box3().setFromObject(ground,true),post=new Box3().setFromObject(stand,true);
  const bgap=pbox.min.y-b.max.y,pgap=Math.max(post.min.x-pbox.max.x,pbox.min.z-post.max.z);
  assert.ok(bgap>.40&&pgap>.03); minGround=Math.min(minGround,bgap);minStand=Math.min(minStand,pgap);
  const x=V().setFromMatrixColumn(beam.matrixWorld,0);
  const angle=Math.atan2(x.y,x.x)*180/Math.PI;
  if(i>=110)assert.ok(Math.abs(angle)<.001&&Math.abs(weightLocal.x-.361)<2e-6);
  if([0,61,110,132].includes(i))poses.push({time:i/60,angle,beamLocalX:weightLocal.x,panPivotY:wp(pan).y});
}
assert.ok(Math.abs(poses[0].angle-9)<.001);
assert.ok(Math.abs(poses[0].beamLocalX-.126)<2e-6);
assert.ok(poses[3].panPivotY-poses[0].panPivotY>.030);
console.log(JSON.stringify({sha256:createHash('sha256').update(data).digest('hex'),bytes:data.length,issues:Khronos.issues,
  triangles:info.totalTriangleCount,vertices:info.totalVertexCount,drawCalls:info.drawCallCount,meshes:json.meshes.length,materials:json.materials.length,
  samples:133,clip:motion.name,clipSeconds:motion.duration,tracks:types,poses,minSlide,minGround,minStand,maxCenter,maxUp},null,2));

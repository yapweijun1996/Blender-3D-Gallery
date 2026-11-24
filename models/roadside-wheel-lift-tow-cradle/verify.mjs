import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {validateBytes} from 'gltf-validator';
import {Vector3, Raycaster, DoubleSide} from 'three';
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';

const slug='roadside-wheel-lift-tow-cradle';
const b=await readFile(new URL('./exports/'+slug+'.glb',import.meta.url));
const val=await validateBytes(b,{uri:slug+'.glb',maxIssues:1000});
assert.deepEqual([val.issues.numErrors,val.issues.numWarnings,val.issues.numInfos],[0,0,0],JSON.stringify(val.issues));
const raw=JSON.parse(b.subarray(20,20+b.readUInt32LE(12)));
assert.equal(raw.asset.version,'2.0');
assert.deepEqual(raw.buffers.map(x=>x.uri),[undefined]);assert.equal(raw.textures?.length??0,0);
assert.equal(raw.animations?.length??0,0);
const {scene,animations}=await new GLTFLoader().parseAsync(b.buffer.slice(b.byteOffset,b.byteOffset+b.byteLength),'');
scene.updateMatrixWorld(true);
assert.equal(animations.length,0);
const V=(...x)=>new Vector3(...x);
const group=n=>{const o=scene.getObjectByName(n);assert.ok(o,n);return o;};
const get=p=>{let o=[];scene.traverse(n=>{if(n.isMesh&&n.name.startsWith(p))o.push(n);});return o;};
const only=p=>{const o=get(p);assert.equal(o.length,1,p);return o[0];};
const wb=group('REFERENCE_WHEEL').getWorldPosition(V());
assert.ok(wb.distanceTo(V(-.590,.504,.734))<1e-6);
assert.equal(get('Tangent_rubber_seat_insert').length,4);
assert.equal(get('Beneath_rubber_solid_molded_support').length,4);
const tire=only('One_original_unbranded_reference_tire');
const x=-.59, y=.504, z=.734;
const st=.53, ct=Math.sqrt(1-st*st);
const vertices=(obj)=>{
  const p=obj.geometry.getAttribute('position');
  return Array.from({length:p.count},(_,i)=>V().fromBufferAttribute(p,i).applyMatrix4(obj.matrixWorld));
};
const read=(o,d,mesh,far=.40)=>{
  const ms=Array.isArray(mesh)?mesh:[mesh];
  const mat=[...new Set(ms.flatMap(x=>Array.isArray(x.material)?x.material:[x.material]))];
  const old=mat.map(m=>m.side);
  mat.forEach(m=>m.side=DoubleSide);
  try {return new Raycaster(o,d,0,far).intersectObjects(ms,false)[0];}
  finally {mat.forEach((m,i)=>m.side=old[i]);}
};
let minDelta=1,maxDelta=0,samples=0;
const gaps=[];
for(const s of [-1,1]){
  const p=V(0,-ct,-s*st);
  const target=only('Tangent_rubber_seat_insert_X-1_Y'+s);
  const P=vertices(target),T=vertices(tire);
  const d=(Math.min(...P.map(q=>q.clone().sub(wb).dot(p)))-Math.max(...T.map(q=>q.clone().sub(wb).dot(p))))*1000;
  assert.ok(d>.038&&d<.042,JSON.stringify([s,d]));gaps.push(d);
  for(let i=-10;i<=10;i++){
    const origin=V(x+.0027*i,y,z).addScaledVector(p,.20);
    const a=read(origin,p,tire),b=read(origin,p,target);
    assert.ok(a&&b);const gap=(b.distance-a.distance)*1000;
    assert.ok(gap>.15&&gap<.25,[i,gap]);
    minDelta=Math.min(minDelta,gap);maxDelta=Math.max(maxDelta,gap);samples++;
  }
}
const voidMeshes=scene.children;assert.ok(voidMeshes.length);
const physical=get('Beneath_rubber_solid_molded_support').concat(get('Tangent_rubber_seat_insert'),get('Outer_longitudinal_wheel-grid_arm'));
let voidRays=0;
for(const cx of [-.59,.59]) for(let i=-3;i<=3;i++)for(let j=-2;j<=2;j++){
  assert.equal(read(V(cx+.026*i,.43,.734+.013*j),V(0,-1,0),physical,.32),undefined);
  voidRays++;
}
const collar=only('True_hollow_outer_telescoping_collar');
let ringRays=0;
for(const xp of [-.09,-.045,0,.045,.09])for(const yp of [.234,.253,.285,.320,.338]){
  assert.equal(read(V(xp,yp,.42),V(0,0,-1),collar),undefined);ringRays++;
}
for(const xp of [-.106,.106])for(const yp of [.231,.282,.340]){
  const h=read(V(xp,yp,.42),V(0,0,-1),collar);
  assert.ok(h&&Math.abs(h.point.z-.375)<1e-6);ringRays++;
}
const caps=get('Round_cap_highlights_root_joint');
assert.equal(caps.length,2);
for(const s of [-1,1]){
  const h=read(V(s*.27,.355,.129),V(-s,0,0),caps);
  assert.ok(h&&Math.abs(h.point.x-s*.214)<1e-6);
}
console.log(JSON.stringify({sha256:createHash('sha256').update(b).digest('hex'),bytes:b.length,
 triangles:val.info.totalTriangleCount,vertices:val.info.totalVertexCount,drawCalls:val.info.drawCallCount,
 meshes:raw.meshes.length,materials:raw.materials.length,animations:animations.length,
 issues:val.issues,tangentGapsMm:gaps,contactRays:samples,radialRayGapsMm:[minDelta,maxDelta],voidRays,ringRays,axleCapRayHits:caps.length},null,2));

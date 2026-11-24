import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {validateBytes} from 'gltf-validator';
import {Raycaster,Vector3,DoubleSide} from 'three';
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';

const id='deepavali-rangoli-pattern-sieve';
const bin=await readFile(new URL('./exports/'+id+'.glb',import.meta.url));
const validation=await validateBytes(bin,{uri:id+'.glb',maxIssues:1000});
assert.deepEqual([validation.issues.numErrors,validation.issues.numWarnings,validation.issues.numInfos],[0,0,0],JSON.stringify(validation.issues));
const j=JSON.parse(bin.subarray(20,20+bin.readUInt32LE(12)));
assert.equal(j.asset.version,'2.0');assert.deepEqual(j.buffers.map(b=>b.uri),[undefined]);assert.equal(j.images?.length??0,0);assert.equal(j.animations?.length??0,0);
const {scene,animations}=await new GLTFLoader().parseAsync(bin.buffer.slice(bin.byteOffset,bin.byteOffset+bin.byteLength),'');
scene.updateMatrixWorld(true);assert.equal(animations.length,0);
const exact=name=>{const o=scene.getObjectByName(name);assert.ok(o,name);return o;};
const source=exact('PERFORATED_SIEVE_HOLDER'),board=exact('PRESENTATION_BASE'),plate=exact('PATTERN_SIEVE_TRUE_PERFORATED_PLATE'),
    pow=exact('MATCHED_POWDER_SWATCH');
const meshes=(roots,search=()=>true)=>{const set=[];for(const root of roots)root.traverse(n=>{if(n.isMesh&&search(n))set.push(n);});return set;};
const faces=meshes([plate]);
const etched=faces.filter(m=>m.material.name.startsWith('Bare cut surfaces'));
assert.equal(etched.length,1);assert.ok(faces.length>1);
const all=meshes([source,board]), powder=meshes([pow],m=>m.name.startsWith('MATCHED_POWDER_TRANSFER_'));
assert.equal(powder.length,4);
const V=(...x)=>new Vector3(...x);
const inv=source.matrixWorld.clone().invert();
const v0=etched[0],T=inv.clone().multiply(v0.matrixWorld), pos=v0.geometry.getAttribute('position'),
  index=v0.geometry.getIndex();
const p=Array.from({length:pos.count},(_,i)=>V().fromBufferAttribute(pos,i).applyMatrix4(T));
const [lo,hi]=[Math.min(...p.map(t=>t.y)),Math.max(...p.map(t=>t.y))];
assert.ok(Math.abs(hi-lo-.0034)<1e-6);
const A=new Map();
const keyof=x=>[x.x,-x.z].map(t=>Math.round(1e6*t)/1e6).join(',');
function join(a,b){assert.notEqual(a,b);if(!A.has(a))A.set(a,new Set());A.get(a).add(b);}
for(let i=0;i<index.count;i+=3){
 let tri=[0,1,2].map(k=>p[index.getX(i+k)]);
 for(let k=0;k<3;k++){
  const a=tri[k],b=tri[(k+1)%3];
  if(a.y>.0016&&b.y>.0016){join(keyof(a),keyof(b));join(keyof(b),keyof(a));}
 }
}
assert.ok([...A.values()].every(x=>x.size===2));
const todo=new Set(A.keys()),loops=[];
while(todo.size){
 const it=todo.values().next().value;
 const loop=[it];let back=it, cur=A.get(it).values().next().value;
 while(cur!==it){loop.push(cur);const rest=[...A.get(cur)].filter(x=>x!==back);assert.equal(rest.length,1);back=cur;cur=rest[0];}
 loop.forEach(q=>todo.delete(q));loops.push(loop.map(x=>x.split(',').map(Number)));
}
assert.equal(loops.length,30);
const cc=(L,fn)=>L.map((v,i)=>fn(v,L[(i+1)%L.length]));
const area=L=>Math.abs(cc(L,(a,b)=>a[0]*b[1]-a[1]*b[0]).reduce((a,b)=>a+b,0))/2;
loops.sort((a,b)=>area(b)-area(a));
const [outer,...holes]=loops;assert.ok(area(outer)>.03&&area(holes[0])<.001);
const isInside=([x,y],L)=>cc(L,([x0,y0],[x1,y1])=>((y0>y)!=(y1>y))&&x<x0+(x1-x0)*(y-y0)/(y1-y0)).reduce((a,b)=>a!==b,false);
function distance([x,y],[a,b],[c,d]){
 const s=c-a,t=d-b,k=Math.max(0,Math.min(1,((x-a)*s+(y-b)*t)/(s*s+t*t)));
 return Math.hypot(x-a-k*s,y-b-k*t);
}
const indexKey=all.concat(powder);
const materials=new Set(indexKey.map(o=>o.material));for(const m of materials)m.side=DoubleSide;
function ray(root,xyz,d,far,objects){
 const o=V(xyz[0],xyz[2],-xyz[1]).applyMatrix4(root.matrixWorld);
 const dir=V(d[0],d[2],-d[1]).transformDirection(root.matrixWorld);
 return new Raycaster(o,dir,0,far).intersectObjects(objects,false)[0];
}
let through=0, transfers=0, walls=0;
for(const h of holes){
 const X=h.map(p=>p[0]),Y=h.map(p=>p[1]), x0=Math.min(...X), x1=Math.max(...X), y0=Math.min(...Y),y1=Math.max(...Y);
 let best=[];
 for(let i=1;i<16;i++)for(let k=1;k<16;k++){
  const q=[x0+(x1-x0)*i/16,y0+(y1-y0)*k/16];
  if(isInside(q,h)) best.push([Math.min(...cc(h,(a,b)=>distance(q,a,b))),q]);
 }
 best=best.sort((a,b)=>b[0]-a[0]);assert.ok(best.length>=3);
 const points=best.filter(x=>x[0]>.00085).slice(0,6);
 assert.equal(points.length,6);
 for(const [sep,q] of points){
  for(const s of [-1,1]){
   assert.equal(ray(source,[...q,s*.017],[0,0,-s],.034,all),undefined);
   through++;
  }
  const strike=ray(pow,[...q,.018],[0,0,-1],.016,powder);
  assert.ok(strike);transfers++;
 }
 for(const s of [-1,1]){
  const q=best[0][1], a=ray(source,[...q,0],[s,0,0],.023,etched);
  assert.ok(a&&a.distance>.0007);walls++;
 }
}
console.log(JSON.stringify({sha256:createHash('sha256').update(bin).digest('hex'),bytes:bin.length,
 triangles:validation.info.totalTriangleCount,vertices:validation.info.totalVertexCount,drawCalls:validation.info.drawCallCount,
 meshes:j.meshes.length,materials:j.materials.length,animations:animations.length,issues:validation.issues,
 actualCutouts:holes.length,thicknessMm:(hi-lo)*1000,completeStationRays:through,powderMatchRays:transfers,boreSidewallRays:walls},null,2));

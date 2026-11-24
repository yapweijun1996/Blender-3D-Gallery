import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {readFile} from 'node:fs/promises';
import {validateBytes} from 'gltf-validator';
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';
import {Box3,Raycaster,Vector3} from 'three';
const id='straddle-beam-monorail-bogie-cutaway';
const bytes=await readFile(process.argv[2]??new URL('./exports/'+id+'.glb',import.meta.url));
const raw=JSON.parse(bytes.subarray(20,20+bytes.readUInt32LE(12)));
const v=await validateBytes(new Uint8Array(bytes),{uri:id+'.glb'});
for(const k of ['numErrors','numWarnings','numInfos','numHints'])assert.equal(v.issues[k],0,JSON.stringify(v.issues));
assert.deepEqual(raw.buffers.map(x=>x.uri),[undefined]);
for(const k of ['images','animations','cameras'])assert.equal(raw[k]?.length??0,0);
const {scene}=await new GLTFLoader().parseAsync(bytes.buffer.slice(bytes.byteOffset,bytes.byteOffset+bytes.byteLength),'');
scene.updateMatrixWorld(true);
const exhibit=scene.getObjectByName('EXHIBIT_BASE'), beam=scene.getObjectByName('SINGLE_STRADDLE_BEAM'), bogie=scene.getObjectByName('SCHEMATIC_SADDLE_BOGIE');
assert.ok(exhibit&&beam&&bogie);
const meshes=(root,name)=>root.children.filter(o=>o.name.startsWith(name));
const nested=(root,name)=>{
  const result=[];
  root.traverse(o=>{if(o.name.startsWith(name)&&!o.parent?.name.startsWith(name))result.push(o);});
  return result;
};
const box=o=>new Box3().setFromObject(o,true);
const near=(a,b,e=2e-6)=>assert.ok(Math.abs(a-b)<e,[a,b,e].join());
const ray=(p,d,root,distance)=>new Raycaster(p,d,0,distance).intersectObject(root,true)[0];
const faces=meshes(beam,'Flat_');
assert.equal(faces.length,5);
const contacts={};
for(const [key,tag,surface,axis,count] of [
 ['top','TOP_LOAD_TYRE','Flat_TOP_load',1,2],
 ['guide','SIDE_GUIDE_TYRE','Flat_SIDE_guide',0,4],
 ['stabilizer','LOWER_STABILIZER_TYRE','Flat_SIDE_stabilizer',0,4]
]){
 const a=nested(bogie,tag);assert.equal(a.length,count);
 const ds=[];
 for(const w of a){
   const b=box(w),c=b.getCenter(new Vector3());
   const s=axis===1||c.x>0?1:-1;
   const f=faces.find(q=>q.name.startsWith(surface)&&(axis===1||Math.sign(box(q).getCenter(new Vector3()).x)===s));
   assert.ok(f);const bb=box(f), face=(s>0?bb.max:bb.min).getComponent(axis);
   const at=(s>0?b.min:b.max).getComponent(axis);near(at,face);
   const direction=new Vector3().setComponent(axis,s);
   for(const shift of axis===1?[-.007,0,.007]:[-.015,.013,.020]){
     const p=c.clone().setComponent(axis,face+s*.009);
     if(axis===1)p.x+=shift;else p.y+=shift;
     const h=ray(p,direction.clone().negate(),f,.011);
     p.setComponent(axis,face-s*.008);
     const t=ray(p,direction,w,.012);
     assert.ok(h&&t,[w.name,f.name,shift].join());
     near(h.point.getComponent(axis),t.point.getComponent(axis));
     ds.push(Math.abs(h.point.getComponent(axis)-t.point.getComponent(axis))*1000);
   }
 }
 contacts[key]={count,rays:ds.length,maxAbsGapMm:Math.max(...ds)};
}
const anchors={
 transverse:nested(bogie,'Saddle_cross_brace').length,
 spindles:nested(bogie,'Continuous_load_spindle').length,
 guidePins:nested(bogie,'SIDE_GUIDE_exposed_seated_kingpin').length,
 stabilizerPins:nested(bogie,'LOWER_STABILIZER_exposed_seated_kingpin').length
};
assert.deepEqual(anchors,{transverse:2,spindles:4,guidePins:4,stabilizerPins:4});
const bbox=box(scene),i=v.info;
console.log(JSON.stringify({sha256:createHash('sha256').update(bytes).digest('hex'),bytes:bytes.length,issues:v.issues,triangles:i.totalTriangleCount,vertices:i.totalVertexCount,drawCalls:i.drawCallCount,meshes:raw.meshes.length,materials:raw.materials.length,contacts,anchors,bounds:[bbox.min.toArray(),bbox.max.toArray()]},null,2));

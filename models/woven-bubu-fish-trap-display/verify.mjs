import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {readFile} from 'node:fs/promises';
import {validateBytes} from 'gltf-validator';
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';
import {Box3,Raycaster,Vector3} from 'three';
const id='woven-bubu-fish-trap-display';
const bytes=await readFile(process.argv[2]??new URL('./exports/'+id+'.glb',import.meta.url));
const raw=JSON.parse(bytes.subarray(20,20+bytes.readUInt32LE(12)));
const k=await validateBytes(new Uint8Array(bytes),{uri:id+'.glb'});
for(const key of ['numErrors','numWarnings','numInfos','numHints'])assert.equal(k.issues[key],0,JSON.stringify(k.issues));
assert.deepEqual(raw.buffers.map(x=>x.uri),[undefined]);
for(const key of ['images','animations','cameras'])assert.equal(raw[key]?.length??0,0);
const {scene:model}=await new GLTFLoader().parseAsync(bytes.buffer.slice(bytes.byteOffset,bytes.byteOffset+bytes.byteLength),'');
model.updateMatrixWorld(true);
for(const n of ['WOVEN_BUBU_STATIC_EXHIBIT','INDEPENDENT_DISPLAY_BASE_AND_CRADLES','OPEN_WOVEN_BAMBOO_OUTER_BASKET','SEPARATE_INWARD_FUNNEL_AND_CLEAR_THROAT'])assert.ok(model.getObjectByName(n),n);
const matches=(p)=>{const a=[];model.traverse(n=>{if(n.isMesh&&n.name.startsWith(p))a.push(n)});return a.sort((a,b)=>a.name.localeCompare(b.name));};
const cast=(at,v,obj,far)=>new Raycaster(at,v,0,far).intersectObjects(obj,false)[0];
const zCenter=.410;
const radial=(x,a,r)=>new Vector3(x,zCenter+r*Math.cos(a),-r*Math.sin(a));
const belt=[];
for(const [tag,n,c,edge,st] of [['Outer',34,21,-.549,.057],['Inset',26,7,-.536,.039]]){
 const warp=matches(tag+'_longitudinal_strip'),weft=matches(tag+'_closed_transverse_weft_band');
 assert.equal(warp.length,n);assert.equal(weft.length,c);
 const g=[];
 for(let i=0;i<n;i++){
  const a=2*Math.PI*i/n;
  const d=new Vector3(0,Math.cos(a),-Math.sin(a));
  for(let j=0;j<c;j++){
   const x=edge+st*j,even=(i+j)%2===0;
   const hi=cast(radial(x,a,0),d,[even?warp[i]:weft[j]],.42);
   const lo=cast(radial(x,a,.34),d.clone().negate(),[even?weft[j]:warp[i]],.34);
   assert.ok(hi&&lo,[i,j,hi,lo]);
   const delta=radial(x,a,0).distanceTo(hi.point)-radial(x,a,0).distanceTo(lo.point);
   assert.ok(delta>.0031&&delta<.0098,[tag,i,j,delta]);g.push(delta);
  }
 }
 belt.push({tag,crossings:g.length,gapMm:[Math.min(...g)*1000,Math.max(...g)*1000]});
}
const rim=matches('Inner_throat_physical_open_edge_binder');
const throat=matches('Inset_').concat(rim,matches('Original_narrow_rounded_entrance_face_lip'));
assert.equal(rim.length,1);
const dir=new Vector3(1,0,0);
let clear=0;
for(const r of [0,.029,.051,.071])for(let j=0;j<12;j++){
 assert.equal(cast(radial(-.72,j*Math.PI/6,r),dir,throat,.53),undefined);clear++;
}
for(let j=0;j<12;j++){
 const h=cast(radial(-.72,j*Math.PI/6,.080),dir,rim,.53);
 assert.ok(h&&h.point.x>-.263&&h.point.x<-.228);
}
const bbox=new Box3().setFromObject(model,true),info=k.info;
console.log(JSON.stringify({sha256:createHash('sha256').update(bytes).digest('hex'),bytes:bytes.length,issues:k.issues,triangles:info.totalTriangleCount,vertices:info.totalVertexCount,drawCalls:info.drawCallCount,meshes:raw.meshes.length,materials:raw.materials.length,belt,throatRays:clear,throatEdgeRays:12,bounds:[bbox.min.toArray(),bbox.max.toArray()]},null,2));

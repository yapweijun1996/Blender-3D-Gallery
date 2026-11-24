import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {readFile} from 'node:fs/promises';
import {validateBytes} from 'gltf-validator';
const id='heritage-rubber-sheet-roller';
const read=k=>readFile(new URL(k,import.meta.url));
const [glb,blend,webp]=await Promise.all([read('exports/'+id+'.glb'),read(id+'.blend'),read('previews/studio.webp')]);
const sha=b=>createHash('sha256').update(b).digest('hex');
const rep=await validateBytes(glb,{uri:id+'.glb'});
assert.equal(rep.issues.messages.length,0,JSON.stringify(rep.issues));
const len=glb.readUInt32LE(12),j=JSON.parse(glb.subarray(20,20+len)), bin=glb.subarray(28+len);
assert.equal(j.asset.version,'2.0');assert.ok(j.buffers.every(x=>!x.uri));
for(const k of ['animations','images','cameras','skins','textures'])assert.equal(j[k]?.length??0,0,k);
const nodes=Object.fromEntries(j.nodes.map(n=>[n.name,n]));
const required=['RUBBER_ROLLER_SMOOTH_LOWER','RUBBER_ROLLER_RIBBED_UPPER','RUBBER_MOCK_SHEET_RIBBED_OUTFEED',
 'RUBBER_FIXED_HAND_CRANK','INLET_WORKTRAY_SLATS','OUTFEED_WORKTRAY_SLATS'];
for(const n of required)assert.ok(Number.isInteger(nodes[n]?.mesh),n);
for(const n of Object.keys(nodes))assert.doesNotMatch(n,/^Studio|\bcamera\b|\blight\b/i);
function values(k){
 const x=j.accessors[k],y=j.bufferViews[x.bufferView],start=(x.byteOffset||0)+(y.byteOffset||0);
 return Array.from({length:x.count},(_,i)=>[0,1,2].map(n=>bin.readFloatLE(start+i*(y.byteStride||12)+4*n)));
}
const profiles=required.slice(0,2).map((name,k)=>{
 const P=j.meshes[nodes[name].mesh].primitives.flatMap(p=>values(p.attributes.POSITION));
 const r=P.map(([x,y,z])=>Math.hypot(y-[.691,.865][k],z));
 const min=Math.min(...r), max=Math.max(...r);
 assert.ok(Math.abs(max-.083)<1e-6&&Math.abs(min-[.083,.0782][k])<1e-6);
 assert.ok(Math.abs(Math.max(...P.map(v=>v[0]))-Math.min(...P.map(v=>v[0]))-.588)<1e-6);
 return {name,min,max};
});
assert.equal(webp.toString('ascii',0,4),'RIFF');assert.equal(webp.toString('ascii',8,12),'WEBP');
const m={glb_bytes:glb.length,glb_sha256:sha(glb),source_sha256:sha(blend),preview_sha256:sha(webp),preview_bytes:webp.length,
 triangles:rep.info.totalTriangleCount,vertices:rep.info.totalVertexCount,draw_calls:rep.info.drawCallCount,meshes:j.meshes.length,
 materials:j.materials.length,animations:0,maximum_texture_dimension_px:0};
assert.ok(m.glb_bytes<225000&&m.triangles<12000);
if(!process.argv.includes('--measure')){
 const md=JSON.parse(await read('metadata.json'));
 assert.deepEqual(m,Object.fromEntries(Object.keys(m).map(k=>[k,md.metrics[k]])));
 assert.equal(md.id,id);
}
console.log(JSON.stringify({id,metrics:m,profiles,issues:rep.issues}));

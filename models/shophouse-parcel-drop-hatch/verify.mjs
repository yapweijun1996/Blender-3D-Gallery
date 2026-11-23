import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { readFile } from 'node:fs/promises';
import { validateBytes } from 'gltf-validator';

const id='shophouse-parcel-drop-hatch';
const load=name=>readFile(new URL(name,import.meta.url));
const [bytes,blend,preview]=await Promise.all([load('exports/'+id+'.glb'),load(id+'.blend'),load('previews/studio.webp')]);
const report=await validateBytes(bytes,{uri:id+'.glb'});
assert.equal(report.issues.messages.length,0,JSON.stringify(report.issues));
const sha=b=>createHash('sha256').update(b).digest('hex');
const jsonBytes=bytes.readUInt32LE(12);
const j=JSON.parse(bytes.subarray(20,20+jsonBytes)), bin=bytes.subarray(28+jsonBytes);
assert.equal(j.asset.version,'2.0');
assert.ok(j.buffers.every(b=>!b.uri));
assert.ok(j.nodes.every(n=>!n.camera&&!n.name?.startsWith('Studio')));
for(const key of ['images','skins','cameras']) assert.equal(j[key]?.length??0,0,key);

function findNode(name){
 const ii=j.nodes.map((node,i)=>node.name===name?i:null).filter(i=>i!==null);
 assert.equal(ii.length,1,name); return ii[0];
}
function measureVec(actual,expected){
 assert.equal(actual.length,expected.length);
 assert.ok(actual.every((x,i)=>Math.abs(x-expected[i])<1e-5),JSON.stringify({actual,expected}));
}
function va(i,arity){
 const a=j.accessors[i], v=j.bufferViews[a.bufferView];
 assert.equal(a.componentType,5126); const stride=v.byteStride||4*arity;
 return Array.from({length:a.count},(_,i)=>Array.from({length:arity},(_,k)=>bin.readFloatLE((v.byteOffset||0)+(a.byteOffset||0)+stride*i+4*k)));
}
const flap=findNode('PARCEL_DROP_FLAP'), parcel=findNode('PARCEL_DROP_SAMPLE');
measureVec(j.nodes[flap].translation,[0,.853,.175]);
measureVec(j.nodes[parcel].translation,[.011,.942,-.116]);
assert.ok(j.nodes[flap].children?.length&&j.nodes[parcel].children?.length);
const [clip]=j.animations;assert.equal(j.animations.length,1);assert.equal(clip.name,'PARCEL_HATCH_OPEN');
assert.equal(clip.channels.length,1);assert.equal(clip.samplers.length,1);
assert.deepEqual(clip.channels[0].target,{node:flap,path:'rotation'});
const samp=clip.samplers[clip.channels[0].sampler], times=va(samp.input,1).flat(), rotation=va(samp.output,4);
assert.ok((samp.interpolation??'LINEAR')==='LINEAR');assert.equal(times.length,rotation.length);
assert.ok(Math.abs(times[0])<1e-5&&Math.abs(times.at(-1)-1.8)<1e-5);
const angles=rotation.map(([x,y,z,w])=>{
 assert.ok(Math.abs(y)<1e-5&&Math.abs(z)<1e-5&&Math.abs(Math.hypot(x,y,z,w)-1)<1e-5&&w>0);
 return 2*Math.atan2(x,w)*180/Math.PI;
});
assert.ok(times.every((time,i)=>i===0||time>times[i-1]));
assert.ok(angles.every((n,i)=>!i||n+1e-5>=angles[i-1]));
assert.ok(Math.abs(angles[0])<1e-4&&Math.abs(angles.at(-1)-70)<1e-4);
assert.ok(times.every((t,i)=>t<1.21||Math.abs(angles[i]-70)<1e-4));
assert.equal(preview.toString('ascii',0,4),'RIFF');
assert.equal(preview.toString('ascii',8,12),'WEBP');
const info=report.info, metrics={
  glb_bytes:bytes.length,glb_sha256:sha(bytes),source_sha256:sha(blend),
  preview_sha256:sha(preview),preview_bytes:preview.length,triangles:info.totalTriangleCount,
  vertices:info.totalVertexCount,draw_calls:info.drawCallCount,meshes:j.meshes.length,
  materials:j.materials.length,animations:1,maximum_texture_dimension_px:0
};
assert.ok(metrics.glb_bytes<800000&&metrics.triangles<50000);
const budget=Object.fromEntries(Object.entries(j.bufferViews.reduce((res,v)=>{const k=v.target===34962?'vertexDataBytes':v.target===34963?'indexBytes':'unspecifiedViewsBytes';res[k]=(res[k]||0)+v.byteLength;return res;},{})).sort());
const clipViews=new Set([j.accessors[samp.input].bufferView,j.accessors[samp.output].bufferView]);
budget.animationSampleBytes=[...clipViews].reduce((n,i)=>n+j.bufferViews[i].byteLength,0);
budget.glbJSONBytes=jsonBytes;
budget.binBytes=bin.length;
const groups={};
for(const n of j.nodes){
 if(n.mesh==null)continue;
 const m=j.meshes[n.mesh], key=n.name.split(' | ')[0];
 const vv=new Set(m.primitives.flatMap(p=>Object.values(p.attributes).concat(p.indices)).map(i=>j.accessors[i].bufferView));
 groups[key]=(groups[key]??0)+[...vv].reduce((s,i)=>s+j.bufferViews[i].byteLength,0);
}
if(!process.argv.includes('--measure')) {
 const md=JSON.parse(await load('metadata.json'));
 assert.deepEqual(metrics,Object.fromEntries(Object.keys(metrics).map(k=>[k,md.metrics[k]])));
 assert.equal(md.id,id);
}
console.log(JSON.stringify({id,metrics,budget,groupBufferViewBytes:groups,clip:{name:clip.name,sampleCount:times.length,duration:times.at(-1),degreesStart:angles[0],degreesEnd:angles.at(-1)},issues:report.issues}));

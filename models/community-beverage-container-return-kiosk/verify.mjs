import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {readFile} from 'node:fs/promises';
import {validateBytes} from 'gltf-validator';
const id='community-beverage-container-return-kiosk';
const load=n=>readFile(new URL(n,import.meta.url));
const [glb,blend,img]=await Promise.all([load('exports/'+id+'.glb'),load(id+'.blend'),load('previews/studio.webp')]);
const sha=b=>createHash('sha256').update(b).digest('hex');
const jr=await validateBytes(glb,{uri:id+'.glb'});
assert.equal(jr.issues.messages.length,0,JSON.stringify(jr.issues));
const bytes=glb.readUInt32LE(12),j=JSON.parse(glb.subarray(20,20+bytes)),bin=glb.subarray(28+bytes);
assert.equal(j.asset.version,'2.0');
assert.ok(j.buffers.every(b=>!b.uri));
for(const k of ['images','cameras','skins'])assert.equal(j[k]?.length??0,0);
function node(name){const x=j.nodes.map((o,i)=>o.name===name?i:null).filter(i=>i!==null);assert.equal(x.length,1);return x[0];}
const can=node('BCR_SAMPLE_CAN'), flag=node('BCR_ACCEPT_FLAG');
const eq=(x,y,eps=1e-5)=>assert.ok(Math.abs(x-y)<eps,JSON.stringify({value:x,expected:y}));
function vec(x,y){assert.equal(x.length,y.length);x.forEach((v,i)=>eq(v,y[i]));}
vec(j.nodes[can].translation,[0,1.09,.26]);vec(j.nodes[flag].translation,[.263,1.154,.343]);assert.ok(j.nodes[can].children?.length&&j.nodes[flag].children?.length);
const [clip]=j.animations;assert.equal(j.animations.length,1);assert.equal(clip.name,'BCR_SAMPLE_ACCEPT');
assert.equal(clip.channels.length,2);assert.equal(clip.samplers.length,2);
const chan=Object.fromEntries(clip.channels.map(c=>[c.target.path,c]));
assert.deepEqual(chan.translation.target,{node:can,path:'translation'});assert.deepEqual(chan.rotation.target,{node:flag,path:'rotation'});
function acc(id,n) {
 const a=j.accessors[id],v=j.bufferViews[a.bufferView];
 assert.equal(a.componentType,5126);
 return Array.from({length:a.count},(_,i)=>Array.from({length:n},(_,k)=>bin.readFloatLE((a.byteOffset||0)+(v.byteOffset||0)+i*(v.byteStride||4*n)+4*k)));
}
function track(key,n){
 const s=clip.samplers[chan[key].sampler];assert.equal(s.interpolation??'LINEAR','LINEAR');
 const t=acc(s.input,1).flat(),v=acc(s.output,n);
 assert.equal(t.length,v.length);eq(t[0],0);eq(t.at(-1),2);
 assert.ok(t.every((a,i)=>!i||a>t[i-1]));
 return [t,v];
}
const [tcan,pos]=track('translation',3);
const [tflag,quat]=track('rotation',4);
for(const [x,y,z] of pos){eq(x,0);eq(y,1.09);assert.ok(z>=-.16501&&z<=.26001);}
assert.ok(pos.every((a,i)=>!i||a[2]<=pos[i-1][2]+1e-5));
vec(pos[0],[0,1.09,.26]);vec(pos.at(-1),[0,1.09,-.165]);
tcan.forEach((t,i)=>{if(t>1.2999)eq(pos[i][2],-.165)});
const angles=quat.map(([x,y,z,w])=>{
 eq(x,0);eq(z,0);eq(Math.hypot(x,y,z,w),1);
 let a=2*Math.atan2(y,w)*180/Math.PI;
 if(a>180.001)a=360-a;
 return Math.abs(a);
});
assert.ok(angles.every((a,i)=>!i||a+1e-5>=angles[i-1]));
eq(angles[0],0);eq(angles.at(-1),180,.001);
tflag.forEach((t,i)=>{if(t<1.3001)eq(angles[i],0);if(t>1.6999)eq(angles[i],180,.001)});
const metrics={glb_bytes:glb.length, glb_sha256:sha(glb),source_sha256:sha(blend),preview_sha256:sha(img),preview_bytes:img.length,
 triangles:jr.info.totalTriangleCount, vertices:jr.info.totalVertexCount,draw_calls:jr.info.drawCallCount,
 meshes:j.meshes.length,materials:j.materials.length,animations:1,maximum_texture_dimension_px:0};
assert.ok(metrics.glb_bytes<270000&&metrics.triangles<20000);
assert.equal(img.toString('ascii',0,4),'RIFF');assert.equal(img.toString('ascii',8,12),'WEBP');
if(!process.argv.includes('--measure')){
 const md=JSON.parse(await load('metadata.json'));
 assert.equal(md.id,id); assert.deepEqual(metrics,Object.fromEntries(Object.keys(metrics).map(k=>[k,md.metrics[k]])));
}
console.log(JSON.stringify({id,metrics,clip:clip.name,translationSamples:tcan.length,rotationSamples:tflag.length,
 canEnd:pos.at(-1),flagEndDegrees:angles.at(-1),issues:jr.issues}));

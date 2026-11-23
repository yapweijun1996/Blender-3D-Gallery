import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {readFile} from 'node:fs/promises';
import {validateBytes} from 'gltf-validator';
const id='shophouse-lane-convex-mirror';
const read=k=>readFile(new URL(k,import.meta.url));
const [glb,blend,webp]=await Promise.all([read('exports/'+id+'.glb'),read(id+'.blend'),read('previews/studio.webp')]);
const sha=b=>createHash('sha256').update(b).digest('hex');
const rep=await validateBytes(glb,{uri:id+'.glb'});
assert.equal(rep.issues.messages.length,0,JSON.stringify(rep.issues));
const count=glb.readUInt32LE(12), j=JSON.parse(glb.subarray(20,20+count)),bin=glb.subarray(28+count);
assert.equal(j.asset.version,'2.0');assert.ok(j.buffers.every(x=>!x.uri));
for(const k of ['animations','images','cameras','skins','textures'])assert.equal(j[k]?.length??0,0,k);
const glass=j.nodes.findIndex(n=>n.name==='CONVEX_LENS_DECORATIVE_CAP');
const parent=j.nodes.find(x=>x.name==='MIRROR_STATIC_MOUNT');
assert.ok(glass>=0&&parent?.children.includes(glass));
assert.ok(j.nodes.some(n=>n.name==='Actual rear attachment disc'));
const [p]=j.meshes[j.nodes[glass].mesh].primitives;
assert.equal(j.meshes[j.nodes[glass].mesh].primitives.length,1);
assert.ok(Number.isInteger(p.attributes.COLOR_0));
const coords=j.accessors[p.attributes.POSITION], view=j.bufferViews[coords.bufferView];
assert.equal(coords.type,'VEC3');assert.equal(coords.componentType,5126);
function xyz(i){return [0,1,2].map(j=>bin.readFloatLE((coords.byteOffset||0)+(view.byteOffset||0)+i*(view.byteStride||12)+4*j));}
const vs=Array.from({length:coords.count},(_,i)=>xyz(i));
// Blender local -Y becomes glTF local +Z; back and rim are not confused with the forward cap.
const front=vs.filter(v=>v[2]>=.03299);
const sphere=.575,edge=.244;
const theory=r=>.033+Math.sqrt(sphere*sphere-r*r)-Math.sqrt(sphere*sphere-edge*edge);
assert.ok(front.length>450);
const error=Math.max(...front.map(([x,y,z])=>Math.abs(z-theory(Math.hypot(x,y)))));
const sag=Math.max(...front.map(v=>v[2]))-.033;
assert.ok(error<.000004&&sag>.054&&sag<.055,JSON.stringify({error,sag}));
assert.equal(webp.toString('ascii',0,4),'RIFF');assert.equal(webp.toString('ascii',8,12),'WEBP');
const m={glb_bytes:glb.length,glb_sha256:sha(glb),source_sha256:sha(blend),preview_sha256:sha(webp),preview_bytes:webp.length,
 triangles:rep.info.totalTriangleCount,vertices:rep.info.totalVertexCount,draw_calls:rep.info.drawCallCount,meshes:j.meshes.length,
 materials:j.materials.length,animations:0,maximum_texture_dimension_px:0};
assert.ok(m.glb_bytes<250000&&m.triangles<13000);
if(!process.argv.includes('--measure')){
 const md=JSON.parse(await read('metadata.json'));
 assert.deepEqual(m,Object.fromEntries(Object.keys(m).map(k=>[k,md.metrics[k]])));
 assert.equal(md.id,id);
}
console.log(JSON.stringify({id,metrics:m,lensForwardSagM:sag,capFitErrorM:error,issues:rep.issues}));

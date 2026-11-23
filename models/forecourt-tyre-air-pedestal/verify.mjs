import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {readFile} from 'node:fs/promises';
import {validateBytes} from 'gltf-validator';
const id='forecourt-tyre-air-pedestal';
const read=k=>readFile(new URL(k,import.meta.url));
const [glb,blend,webp]=await Promise.all([read('exports/'+id+'.glb'),read(id+'.blend'),read('previews/studio.webp')]);
const sha=b=>createHash('sha256').update(b).digest('hex');
const rep=await validateBytes(glb,{uri:id+'.glb'});
assert.equal(rep.issues.messages.length,0,JSON.stringify(rep.issues));
const count=glb.readUInt32LE(12), j=JSON.parse(glb.subarray(20,20+count));
assert.equal(j.asset.version,'2.0');assert.ok(j.buffers.every(x=>!x.uri));
for(const k of ['animations','images','cameras','skins','textures'])assert.equal(j[k]?.length??0,0,k);
assert.equal(j.extensionsUsed?.includes('KHR_draco_mesh_compression')??false,false);
const nodes=Object.fromEntries(j.nodes.map(n=>[n.name,n]));
const named=['AIR_CONTINUOUS_COIL_AND_LEAD','AIR_CHUCK_SMALL_STOWED_HANDLE','NOZZLE_CRADLE_FORK',
 'Upper cabinet inlet sleeve','Chuck cable flex strain relief','Open reel lower floor',
 'Recess deep back wall','Smoked acrylic instrument face','Fixed ivory pointer in decorative dial','FORCOURT_BILINGUAL_GEOMETRY'];
for(const n of named)assert.ok(Number.isInteger(nodes[n]?.mesh),n);
for(const n of Object.keys(nodes))assert.doesNotMatch(n,/^Studio|\bcamera\b|\blight\b/i);
const [h]=j.meshes[nodes[named[0]].mesh].primitives;
assert.equal(j.meshes[nodes[named[0]].mesh].primitives.length,1);
const v=j.accessors[h.attributes.POSITION],i=j.accessors[h.indices];
// The smooth hose is one named opaque mesh; dimensions are metre-scale in glTF (Y up).
assert.ok(v.min[0]<-.24&&v.max[0]>.35);
assert.ok(v.min[1]<.42&&v.max[1]>1.03);
assert.ok(v.min[2]>.05&&v.max[2]>.26);
assert.equal(i.count/3,2444);
assert.equal(webp.toString('ascii',0,4),'RIFF');assert.equal(webp.toString('ascii',8,12),'WEBP');
const m={glb_bytes:glb.length,glb_sha256:sha(glb),source_sha256:sha(blend),preview_sha256:sha(webp),preview_bytes:webp.length,
 triangles:rep.info.totalTriangleCount,vertices:rep.info.totalVertexCount,draw_calls:rep.info.drawCallCount,meshes:j.meshes.length,
 materials:j.materials.length,animations:0,maximum_texture_dimension_px:0};
assert.ok(m.glb_bytes<210000&&m.triangles<12000);
if(!process.argv.includes('--measure')){
 const md=JSON.parse(await read('metadata.json'));
 assert.deepEqual(m,Object.fromEntries(Object.keys(m).map(k=>[k,md.metrics[k]])));
 assert.equal(md.id,id);
}
console.log(JSON.stringify({id,metrics:m,hoseTriangles:i.count/3,issues:rep.issues}));

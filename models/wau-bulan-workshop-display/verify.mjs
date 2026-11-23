import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {readFile} from 'node:fs/promises';
import {validateBytes} from 'gltf-validator';
const id='wau-bulan-workshop-display';
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
const named=['WAU_BOWED_PAPER_SAIL','WAU_CRESCENT_PAPER_TAIL','WAU_LONGITUDINAL_BAMBOO_SPINE',
 'WAU_CONTINUOUS_BOWED_CROSS_SPAR','WAU_CRESCENT_BOW_SPAR','WAU_BRIDLE_UPPER','WAU_BRIDLE_LOWER',
 'WAU_ORIGINAL_LAYERED_APPLIQUE','WORKSHOP_BAMBOO_STAND','WORKSHOP_COTTON_REEL'];
for(const n of named)assert.ok(Number.isInteger(nodes[n]?.mesh),n);
for(const n of Object.keys(nodes))assert.doesNotMatch(n,/^Studio|camera|light/i);
function bounds(node){
 const accs=j.meshes[nodes[node].mesh].primitives.map(p=>j.accessors[p.attributes.POSITION]);
 return [0,1,2].map(i=>[Math.min(...accs.map(a=>a.min[i])),Math.max(...accs.map(a=>a.max[i]))]);
}
// glTF x width / +Y up / +Z outward, baked and still metre scale.
const sail=bounds(named[0]),tail=bounds(named[1]), spar=bounds(named[3]),stand=bounds(named[8]);
assert.ok(Math.abs((sail[0][1]-sail[0][0])-1.75)<1e-6);
assert.ok(tail[0][1]-tail[0][0]>.823&&tail[0][1]-tail[0][0]<.825);
const sparBowM=spar[2][1]-spar[2][0];
assert.ok(sparBowM>.076&&sparBowM<.081);
assert.equal(stand[1][0],0);assert.ok(stand[1][1]>.98);
assert.equal(webp.toString('ascii',0,4),'RIFF');assert.equal(webp.toString('ascii',8,12),'WEBP');
const m={glb_bytes:glb.length,glb_sha256:sha(glb),source_sha256:sha(blend),preview_sha256:sha(webp),preview_bytes:webp.length,
 triangles:rep.info.totalTriangleCount,vertices:rep.info.totalVertexCount,draw_calls:rep.info.drawCallCount,meshes:j.meshes.length,
 materials:j.materials.length,animations:0,maximum_texture_dimension_px:0};
assert.ok(m.glb_bytes<315000&&m.triangles<14000);
if(!process.argv.includes('--measure')){
 const md=JSON.parse(await read('metadata.json'));
 assert.deepEqual(m,Object.fromEntries(Object.keys(m).map(k=>[k,md.metrics[k]])));
 assert.equal(md.id,id);
}
console.log(JSON.stringify({id,metrics:m,sparBowM,issues:rep.issues}));

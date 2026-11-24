import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {readFile} from 'node:fs/promises';
import {validateBytes} from 'gltf-validator';
const id='void-deck-xiangqi-table';
const read=k=>readFile(new URL(k,import.meta.url));
const [glb,blend,webp]=await Promise.all([read('exports/'+id+'.glb'),read(id+'.blend'),read('previews/studio.webp')]);
const sha=b=>createHash('sha256').update(b).digest('hex');
const rep=await validateBytes(glb,{uri:id+'.glb'});
assert.equal(rep.issues.messages.length,0,JSON.stringify(rep.issues));
const len=glb.readUInt32LE(12),j=JSON.parse(glb.subarray(20,20+len));
assert.equal(j.asset.version,'2.0');assert.ok(j.buffers.every(x=>!x.uri));
for(const k of ['animations','images','cameras','skins','textures'])assert.equal(j[k]?.length??0,0,k);
const nodes=Object.fromEntries(j.nodes.map(n=>[n.name,n]));
const core=['TABLE_ROUNDED_CAST_TERRAZZO_TOP','TABLE_SOLID_CAST_TAPER_AND_FOOT','BOARD_FIXED_INTEGRAL_INSET',
 'XIANGQI_INTEGRAL_GRID_RIVER_PALACES','TERRAZZO_RESTRAINED_ORIGINAL_AGGREGATE',
 ...['FRONT','BACK','LEFT','RIGHT'].map(d=>'STOOL_'+d+'_SOLID_CAST_SEAT')];
for(const n of core)assert.ok(Number.isInteger(nodes[n]?.mesh),n);
const slots={
 RED:{GENERAL:[4,0],CHARIOT:[8,2],HORSE:[2,2],CANNON:[7,4],SOLDIER:[4,4]},
 DARK:{GENERAL:[4,9],CHARIOT:[0,7],HORSE:[6,7],CANNON:[1,5],SOLDIER:[6,6]},
};
const used=new Set();
for(const [side,pieces] of Object.entries(slots)){
 for(const [piece,[i,r]] of Object.entries(pieces)){
  const n='XIANGQI_'+side+'_'+piece;
  assert.ok(Number.isInteger(nodes[n]?.mesh));assert.ok(Number.isInteger(nodes[n+'_ENGRAVING']?.mesh));
  const acc=j.accessors[j.meshes[nodes[n].mesh].primitives[0].attributes.POSITION];
  const center=acc.min.map((min,i)=>(min+acc.max[i])/2);
  assert.ok(Math.abs(center[0]-(i-4)*.092)<2e-6&&Math.abs(center[2]+(r-4.5)*.092)<2e-6,n);
  used.add(i+':'+r);
 }
}
assert.equal(used.size,10);assert.ok(used.has('4:0')&&used.has('4:4')&&used.has('4:9'));
for(const n of Object.keys(nodes))assert.doesNotMatch(n,/^Studio|\bcamera\b|\blight\b/i);
assert.equal(webp.toString('ascii',0,4),'RIFF');assert.equal(webp.toString('ascii',8,12),'WEBP');
const m={glb_bytes:glb.length,glb_sha256:sha(glb),source_sha256:sha(blend),preview_sha256:sha(webp),preview_bytes:webp.length,
 triangles:rep.info.totalTriangleCount,vertices:rep.info.totalVertexCount,draw_calls:rep.info.drawCallCount,meshes:j.meshes.length,
 materials:j.materials.length,animations:0,maximum_texture_dimension_px:0};
assert.ok(m.glb_bytes<260000&&m.triangles<14000);
if(!process.argv.includes('--measure')){
 const md=JSON.parse(await read('metadata.json'));
 assert.deepEqual(m,Object.fromEntries(Object.keys(m).map(k=>[k,md.metrics[k]])));
 assert.equal(md.id,id);
}
console.log(JSON.stringify({id,metrics:m,slots,issues:rep.issues}));

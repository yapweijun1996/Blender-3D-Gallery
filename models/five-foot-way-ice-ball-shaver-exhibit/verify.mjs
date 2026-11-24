import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {readFile} from 'node:fs/promises';
import {validateBytes} from 'gltf-validator';
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';
import {Box3,Raycaster,Vector3} from 'three';
const id='five-foot-way-ice-ball-shaver-exhibit';
const bytes=await readFile(process.argv[2]??new URL('./exports/'+id+'.glb',import.meta.url));
const raw=JSON.parse(bytes.subarray(20,20+bytes.readUInt32LE(12)));
const v=await validateBytes(new Uint8Array(bytes),{uri:id+'.glb'});
for(const k of ['numErrors','numWarnings','numInfos','numHints'])assert.equal(v.issues[k],0,JSON.stringify(v.issues));
assert.deepEqual(raw.buffers.map(x=>x.uri),[undefined]);
for(const k of ['images','animations','cameras'])assert.equal(raw[k]?.length??0,0);
const {scene}=await new GLTFLoader().parseAsync(bytes.buffer.slice(bytes.byteOffset,bytes.byteOffset+bytes.byteLength),'');
scene.updateMatrixWorld(true);
const shaver=scene.getObjectByName('ORIGINAL_WOODEN_SHAVER_EXHIBIT'),
 bowlAndIce=scene.getObjectByName('EMPTY_BOWL_AND_SEPARATE_STAGED_ICE');
assert.ok(shaver&&bowlAndIce);
const one=(group,prefix)=>{const g=group.children.filter(o=>o.name.startsWith(prefix));assert.equal(g.length,1,prefix);return g[0];};
const deck=one(shaver,'Continuous_bench_deck'),bowl=one(bowlAndIce,'Closed_thin_enamel_catch_bowl');
const hits=(o,x,z)=>new Raycaster(new Vector3(x,.27,z),new Vector3(0,-1,0),0,.24).intersectObjects(o,true)[0]?.point.y;
let rays=0;
for(const x of [-.048,-.024,0,.024,.048])for(const dy of [-.015,-.006,0,.01,.015]){
 const z=.103-dy;
 assert.equal(hits([deck],x,z),undefined);
 const a=hits([shaver,bowlAndIce],x,z),b=hits([bowl],x,z);
 assert.ok(a&&b&&Math.abs(a-b)<2e-6&&.048999<a&&a<.051);rays++;
}
const ice=one(bowlAndIce,'Frosty_sculpted_demonstration_ice');
const box=o=>new Box3().setFromObject(o,true);
assert.ok(Math.abs(box(ice).min.y-box(deck).max.y)<2e-6);
assert.ok(!raw.nodes.some(n=>/blade/i.test(n.name)));
console.log(JSON.stringify({sha256:createHash('sha256').update(bytes).digest('hex'),bytes:bytes.length,issues:v.issues,triangles:v.info.totalTriangleCount,vertices:v.info.totalVertexCount,meshes:raw.meshes.length,materials:raw.materials.length,drawCalls:v.info.drawCallCount,openSlotRays:rays,emptyBowl:true,static:true},null,2));

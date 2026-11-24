import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {validateBytes} from 'gltf-validator';
import {Raycaster,Vector3} from 'three';
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';

const slug='stair-side-bicycle-wheeling-channel';
const p=new URL('./exports/'+slug+'.glb',import.meta.url);
const bytes=await readFile(p);
const report=await validateBytes(new Uint8Array(bytes),{uri:slug+'.glb',maxIssues:1000});
assert.equal(report.issues.numErrors,0,JSON.stringify(report.issues));
assert.equal(report.issues.numWarnings,0,JSON.stringify(report.issues));
const json=JSON.parse(bytes.subarray(20,20+bytes.readUInt32LE(12)));
assert.equal(json.asset.version,'2.0');assert.deepEqual(json.buffers.map(b=>b.uri),[undefined]);
for(const k of ['images','textures','animations','cameras'])assert.equal(json[k]?.length??0,0);
assert.equal(json.extensions?.KHR_lights_punctual?.lights?.length??0,0);
const gltf=await new GLTFLoader().parseAsync(bytes.buffer.slice(bytes.byteOffset,bytes.byteOffset+bytes.byteLength),'');
const scene=gltf.scene;scene.updateMatrixWorld(true);
const rail='CONTINUOUS_WHEEL_TROUGH';
assert.ok(scene.getObjectByName(rail));
const cast=new Raycaster();
const down=new Vector3(0,-1,0);
function hit(x,y,kind) {
 cast.set(new Vector3(x,1.99,-y),down);
 const h=cast.intersectObject(scene,true)[0];
 assert.ok(h&&h.object.name.startsWith(kind),JSON.stringify([x,y,kind,h?.object.name]));
 return h.point.y;
}
const x0=-1.145,x1=.985,cy=-.492,base=.143,high=.839;
let last=-Infinity,probes=0;
for(let i=0;i<=280;i++){
 const x=x0+.0005+(x1-x0-.001)*i/280;
 const center=hit(x,cy,rail);
 assert.ok(center>=last-4e-7);last=center;
 for(const y of [-.034,.034])assert.ok(Math.abs(hit(x,cy+y,rail)-center)<2e-6);
 probes+=3;
 if(i===0)assert.ok(Math.abs(center-base)<3e-6);
 if(i===280)assert.ok(Math.abs(center-high)<3e-6);
}
let joins=0;
for(const [x,s,deck,z] of [[x0,1,'Lower_cropped_loading_landing_slab',base],[x1,-1,'Narrow_upper_handover_closeout_slab',high]]){
 for(const d of [.0005,.0025,.009])for(const off of [-.033,0,.033]){
  const a=hit(x+s*d,cy+off,rail),b=hit(x-s*d,cy+off,deck);
  assert.ok(Math.abs(a-b)<3e-6&&Math.abs(a-z)<3e-6);joins++;
 }
}
for(const x of [-.83,-.43,-.03,.25,.61]){
 const c=hit(x,cy,rail);
 for(const d of [-.066,.066])assert.ok(hit(x,cy+d,rail)-c>.037);
}
const info=report.info;
console.log(JSON.stringify({sha256:createHash('sha256').update(bytes).digest('hex'),bytes:bytes.length,
  issues:report.issues,triangles:info.totalTriangleCount,vertices:info.totalVertexCount,drawCalls:info.drawCallCount,
  meshes:json.meshes.length,materials:json.materials.length,threeFloorRays:probes,threeHandoverPairs:joins,threeCrownHits:10},null,2));

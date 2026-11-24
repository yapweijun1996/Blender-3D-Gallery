import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {validateBytes} from 'gltf-validator';
import {Raycaster,Vector3} from 'three';
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';

const slug='batik-canting-tool-rest';
const p=new URL('./exports/'+slug+'.glb',import.meta.url);
const data=await readFile(p);
const doc=JSON.parse(data.subarray(20,20+data.readUInt32LE(12)));
const report=await validateBytes(new Uint8Array(data),{uri:slug+'.glb',maxIssues:1000});
assert.equal(report.issues.numErrors,0,JSON.stringify(report.issues));
assert.equal(report.issues.numWarnings,0,JSON.stringify(report.issues));
assert.equal(doc.asset.version,'2.0');
assert.deepEqual(doc.buffers.map(b=>b.uri),[undefined]);
for(const k of ['images','textures','animations','cameras'])assert.equal(doc[k]?.length??0,0);
assert.equal(doc.extensions?.KHR_lights_punctual?.lights?.length??0,0);
const loaded=await new GLTFLoader().parseAsync(data.buffer.slice(data.byteOffset,data.byteOffset+data.byteLength),'');
const scene=loaded.scene;scene.updateMatrixWorld(true);
const copper='CANTING_CONNECTED_COPPER_BOWL_AND_SPOUT';
const c=scene.getObjectByName(copper);assert.ok(c);
const ray=new Raycaster();
const V=(x,y,z)=>new Vector3(x,z,-y);
function cast(origin,dir,far,obj=scene){
 ray.set(origin,dir);ray.far=far;return ray.intersectObject(obj,true)[0];
}
const p0=t=>V(.039+.058*t,-.0044*t*t,.096-.031*t*t);
const T=t=>V(.058,-.0088*t,-.062*t).normalize();
const rad=t=>.00440-.00325*t**.77;
const side=t=>V(0,1,0).addScaledVector(T(t),-V(0,1,0).dot(T(t))).normalize();
const basis=t=>[side(t),T(t).cross(side(t)).normalize()];
const offset=(t,a)=>{const [y,z]=basis(t);return p0(t).addScaledVector(y,.41*rad(t)*Math.cos(a)).addScaledVector(z,.41*rad(t)*Math.sin(a));};
let empty=0; let wall=0; let noIntrusion=0; let bottom=0;
function clear(a,b){
 const dir=b.clone().sub(a);const len=dir.length();dir.normalize();
 assert.equal(cast(a,dir,len,c),undefined);
 assert.equal(cast(b,dir.negate(),len,c),undefined);
 empty+=2;
}
for(const z of [-.0019,0,.0019])for(const y of [-.0019,0,.0019]){
 clear(V(.014,y,.096+z),V(.039,y,.096+z));
}
for(let i=0;i<42;i++)for(let j=0;j<8;j++){
 const a=j*Math.PI/4;clear(offset(i/42,a),offset((i+1)/42,a));
}
clear(p0(1).addScaledVector(T(1),-.0014),p0(1).addScaledVector(T(1),.004));
for(let i=1;i<=25;i++){
 const t=i/26,[y,z]=basis(t);
 for(let j=0;j<12;j++){
   const a=j*Math.PI/6,d=y.clone().multiplyScalar(Math.cos(a)).addScaledVector(z,Math.sin(a));
   const hit=cast(p0(t),d,.014,c);
   assert.ok(hit&&hit.distance>.65*rad(t)&&hit.distance<1.02*rad(t),JSON.stringify([i,j,hit?.distance,rad(t)]));wall++;
 }
}
for(const x of [-.012,-.003,.008,.014]){
 for(const y of [-.007,0,.006]){
   const hit=cast(V(x,y,.163),V(0,0,-1),.14,c);
   assert.ok(hit&&hit.point.y<=.083&&hit.point.y>=.068);bottom++;
 }
}
for(const y of [-.014,-.010,-.007,-.004])for(let j=0;j<=14;j++){
 const o=V(-.008,y,.085+j*.00165);
 const hit=cast(o,V(-1,0,0),.056);
 assert.ok(hit?.object.name.startsWith(copper),JSON.stringify([y,j,hit?.object.name]));noIntrusion++;
}
console.log(JSON.stringify({sha256:createHash('sha256').update(data).digest('hex'),bytes:data.length,
 issues:report.issues,triangles:report.info.totalTriangleCount,vertices:report.info.totalVertexCount,drawCalls:report.info.drawCallCount,
 meshes:doc.meshes.length,materials:doc.materials.length,threeBorePathRays:empty,threeInnerWallProbes:wall,
 threeHardwareSeparationRays:noIntrusion,threeReservoirHits:bottom},null,2));

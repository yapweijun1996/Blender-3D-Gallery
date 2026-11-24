import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {validateBytes} from 'gltf-validator';
import {Raycaster, Vector3} from 'three';
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';

const slug='roti-jala-lace-pouring-cup';
const p=new URL('./exports/'+slug+'.glb',import.meta.url);
const data=await readFile(p);
const report=await validateBytes(new Uint8Array(data),{uri:slug+'.glb',maxIssues:1000});
assert.equal(report.issues.numErrors,0,JSON.stringify(report.issues));
assert.equal(report.issues.numWarnings,0,JSON.stringify(report.issues));
const json=JSON.parse(data.subarray(20,20+data.readUInt32LE(12)));
assert.equal(json.asset.version,'2.0');assert.deepEqual(json.buffers.map(b=>b.uri),[undefined]);
for(const key of ['images','textures','animations','cameras']) assert.equal(json[key]?.length??0,0);
assert.equal(json.extensions?.KHR_lights_punctual?.lights?.length??0,0);
const parsed=await new GLTFLoader().parseAsync(data.buffer.slice(data.byteOffset,data.byteOffset+data.byteLength),'');
const scene=parsed.scene;scene.updateMatrixWorld(true);
const cup=scene.getObjectByName('ROTI_JALA_CUP_LOCAL');
const dish=scene.getObjectByName('ROTI_JALA_SAMPLE_DISH');assert.ok(cup&&dish);
const cast=new Raycaster();
const xyz=(x,y,z)=>new Vector3(x,z,-y);
const dir=(axis,obj)=>axis.transformDirection(obj.matrixWorld);
const ray=(o,d,far)=>{cast.set(o,d);cast.far=far;return cast.intersectObject(scene,true)[0];};
const down=dir(xyz(0,0,-1),cup),up=down.clone().negate();
const coords=[[0,0],[.031,0],[-.031,0],[0,.031],[0,-.031]];
let clear=0,rings=0,holes=0,ribs=0;
for(let i=0;i<coords.length;i++){
 const [x,y]=coords[i];
 for(const r of [.001,.00365])for(let k=0;k<8;k++){
   const t=Math.PI*k/4,u=x+r*Math.cos(t),v=y+r*Math.sin(t);
   assert.equal(ray(cup.localToWorld(xyz(u,v,.153)),down,.188),undefined);
   assert.equal(ray(cup.localToWorld(xyz(u,v,-.033)),up,.178),undefined);clear+=2;
 }
 for(let k=0;k<8;k++){
   const t=Math.PI*k/4,r=.00533;
   const got=ray(cup.localToWorld(xyz(x+r*Math.cos(t),y+r*Math.sin(t),-.044)),up,.027);
   assert.ok(got?.object.name.startsWith('CUP_HOLLOW_NOZZLE_'+(i+1)),JSON.stringify([i,k,got?.object.name]));
   assert.ok(Math.abs(cup.worldToLocal(got.point.clone()).y+.029)<2.5e-5);
   rings++;
 }
}
for(let i=-5;i<5;i++)for(let j=-5;j<5;j++){
 const x=(i+.5)*.018,y=(j+.5)*.018;if(x*x+y*y>.085**2)continue;
 const got=ray(dish.localToWorld(xyz(x,y,.108)),new Vector3(0,-1,0),.066);
 assert.ok(got?.object.name.startsWith('Warm_cream_shallow'),JSON.stringify([i,j,got?.object.name]));holes++;
}
for(let k=-5;k<=5;k++){
 const y=k*.018+.0028*Math.sin(7*.65+k*.72)+.0010*Math.sin(7*.92);
 const got=ray(dish.localToWorld(xyz(0,y,.108)),new Vector3(0,-1,0),.077);
 assert.ok(got?.object.name.startsWith('Physical_roti'),JSON.stringify([k,got?.object.name]));ribs++;
}
assert.ok(holes>=60&&ribs===11);
console.log(JSON.stringify({sha256:createHash('sha256').update(data).digest('hex'),bytes:data.length,
 issues:report.issues,triangles:report.info.totalTriangleCount,vertices:report.info.totalVertexCount,drawCalls:report.info.drawCallCount,
 meshes:json.meshes.length,materials:json.materials.length,engineOpenBoreCasts:clear,engineAnnularNozzleHits:rings,engineLaceGaps:holes,engineLaceRibbons:ribs},null,2));

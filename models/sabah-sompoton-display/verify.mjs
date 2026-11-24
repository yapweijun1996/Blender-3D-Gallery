import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {readFile} from 'node:fs/promises';
import {validateBytes} from 'gltf-validator';
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';
import {Box3,Raycaster,Vector3} from 'three';
const id='sabah-sompoton-display';
const bytes=await readFile(process.argv[2]??new URL('./exports/'+id+'.glb',import.meta.url));
const gltf=JSON.parse(bytes.subarray(20,20+bytes.readUInt32LE(12)));
const k=await validateBytes(new Uint8Array(bytes),{uri:id+'.glb'});
for(const value of ['numErrors','numWarnings','numInfos','numHints'])assert.equal(k.issues[value],0,JSON.stringify(k.issues));
assert.deepEqual(gltf.buffers.map(x=>x.uri),[undefined]);
assert.equal(gltf.images?.length??0,0);
assert.equal(gltf.animations?.length??0,0);
assert.equal(gltf.cameras?.length??0,0);
const g=await new GLTFLoader().parseAsync(bytes.buffer.slice(bytes.byteOffset,bytes.byteOffset+bytes.byteLength),'');
const model=g.scene;model.updateMatrixWorld(true);
const matches=(p)=>{const a=[];model.traverse(n=>{if(n.isMesh&&n.name.startsWith(p))a.push(n)});return a;};
const roots=['SABAH_SOMPOTON_EXHIBIT_ROOT','KOROBU_HOLLOW_DRIED_GOURD','EIGHT_TUBES_IN_TWO_RAFTS','STAND_AND_PLAQUE'];
assert.ok(roots.every(k=>model.getObjectByName(k)));
const whole=matches('Hollow_organic_gourd_shell');
assert.ok(whole.length >=3 && whole.some(n=>n.geometry.hasAttribute('color')));
const minusY=new Vector3(0,-1,0);
const cast=(at,vector,meshes,far=1.5)=>new Raycaster(at,vector,0,far).intersectObjects(meshes,false)[0];
let tubeRays=0;
const tubes=[];
for(const row of ['SHORT','LONG']){
 for(const [i,x] of [.000,.034,.068,.102].entries()){
  const y=row==='SHORT'?.016:-.016;const ms=matches('Hollow_bamboo_stalk_'+row+'_RAFT_'+(i+1));
  assert.ok(ms.length>=3 && ms.some(n=>n.geometry.hasAttribute('color')));
  const top=Math.max(...ms.map(n=>new Box3().setFromObject(n,true).max.y));
  const depths=[];
  for(const [dx,dz] of [[0,0],[.004,0],[-.004,0],[0,.004],[0,-.004]]){
    const h=cast(new Vector3(x+dx,top+.01,y+dz),minusY,ms,.65);
    assert.ok(h);depths.push(top-h.point.y);tubeRays++;
  }
  if(row==='SHORT')assert.ok(depths.every(x=>x>.327&&x<.35));
  else if(i%2===0)assert.ok(depths.every(x=>x>.010&&x<.016));
  else assert.ok(depths.every(x=>x>.0005&&x<.0021));
  tubes.push({row,index:i+1,topM:top,depthM:depths[0]});
 }
}
const start=new Vector3(-.252,.246,.023);
const to=new Vector3(-.210,.226,.017).sub(start).normalize();
const neck=[];
for(const u of [-.002,0,.002])for(const v of [-.002,0,.002]){
 assert.equal(cast(start.clone().add(new Vector3(0,u,v)),to,whole,.046),undefined);
 neck.push([u,v]);
}
assert.equal(matches('Individually_modeled_woven_raft_binding_band').length,8);
const bbox=new Box3().setFromObject(model,true);
assert.ok(bbox.max.y>.78&&bbox.max.y<.785);
const info=k.info;
console.log(JSON.stringify({sha256:createHash('sha256').update(bytes).digest('hex'),bytes:bytes.length,issues:k.issues,triangles:info.totalTriangleCount,vertices:info.totalVertexCount,drawCalls:info.drawCallCount,meshes:gltf.meshes.length,materials:gltf.materials.length,tubes,tubeRays,clearNeckRays:neck.length,bounds:[bbox.min.toArray(),bbox.max.toArray()]},null,2));

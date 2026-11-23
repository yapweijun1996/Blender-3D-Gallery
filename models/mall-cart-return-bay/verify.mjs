import assert from 'node:assert/strict';
import fs from 'node:fs';
import { createHash } from 'node:crypto';
import { fileURLToPath } from 'node:url';
import { Box3, Vector3, Raycaster } from 'three';
import validator from 'gltf-validator';
import { readGlb } from '../mall-floor-tile/glb.mjs';

const slug='mall-cart-return-bay', levels=[];
const hash=bytes=>createHash('sha256').update(bytes).digest('hex');
const local=file=>new URL(file,import.meta.url);
const metadata=JSON.parse(fs.readFileSync(local('metadata.json'),'utf8'));
function near(v,target){ assert.ok(Math.abs(v-target)<1e-6,v+' differs from '+target); }
for (const [i,lod] of ['LOD0','LOD1','LOD2'].entries()) {
  const file='exports/'+slug+(i?'-'+lod.toLowerCase():'')+'.glb';
  const { scene, bytes, json }=await readGlb(fileURLToPath(local(file)));
  const { issues }=await validator.validateBytes(bytes);
  assert.equal(issues.numErrors,0);
  assert.equal(issues.numWarnings,0);
  assert.equal(json.materials.length,4);
  assert.ok(scene.getObjectByName('ASSET_CartReturnBay_'+lod));
  assert.deepEqual(json.images??[],[]);
  assert.ok((json.buffers??[]).every(b=>!b.uri));
  const box=new Box3().setFromObject(scene,true);
  for(const [j,edge] of [box.min.toArray(),box.max.toArray()].entries()) {
    const expected=j?[.80,1.201,.55]:[-.80,0,-.55];
    edge.forEach((val,k)=>near(val,expected[k]));
  }
  const ray=(x,y,z,dx,dy,dz)=>new Raycaster(new Vector3(x,y,z),new Vector3(dx,dy,dz)).intersectObject(scene,true)[0];
  for(const x of [-.75,0,.75])for(const z of [-.50,.50]) {
    near(ray(x,-.01,z,0,1,0).point.y,0);
  }
  for(const x of [-.37,.37])for(const dx of [-.29,0,.29])for(const y of [.04,.19,.60,.88]){
    const hit=ray(x+dx,y,.70,0,0,-1);
    assert.ok(!hit || hit.point.z<-.45,'a barrier intrudes into a cart lane');
  }
  for(const x of [-.375,.375]){
    const panel=ray(x+.160,1.158,.55,0,0,-1);
    assert.equal(panel?.object.material.name,'Deep lagoon enamel');
    const mark=ray(x+(i===2?0:.015),i===2?1.140:1.120,.55,0,0,-1);
    assert.equal(mark?.object.material.name,'Porcelain return marks');
  }
  let triangles=0,draws=0;
  scene.traverse(o=>{
    if(!o.isMesh)return;
    draws++;
    triangles+=(o.geometry.index?.count??o.geometry.getAttribute('position').count)/3;
  });
  if(i){assert.ok(triangles<levels[i-1].triangles);assert.ok(bytes.length<levels[i-1].bytes);}
  levels.push({level:lod,file,triangles,draws,bytes:bytes.length,sha256:hash(bytes)});
}
assert.deepEqual(metadata.levels,levels);
const sourceHash=hash(fs.readFileSync(local(metadata.source)));
const previewHash=hash(fs.readFileSync(local(metadata.preview)));
assert.equal(metadata.sha256.source,sourceHash);
assert.equal(metadata.sha256.preview,previewHash);
assert.equal(metadata.sha256.glb,levels[0].sha256);
console.log(JSON.stringify({levels,sourceHash,previewHash,errors:0,warnings:0},null,2));

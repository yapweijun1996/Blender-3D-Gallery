// Run from the repository root. Geometry tests exercise actual GLB surfaces.
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import fs from 'node:fs/promises';
import {createRequire} from 'node:module';
import {dirname,resolve} from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {parseArgs} from 'node:util';
const base=dirname(fileURLToPath(import.meta.url));
const project=createRequire(resolve('package.json'));
const THREE=await import(new URL('three.module.js',pathToFileURL(project.resolve('three'))).href);
const {validateBytes}=project('gltf-validator');
const {readGlb}=await import(pathToFileURL(resolve('models/mall-floor-tile/glb.mjs')).href);
const args=parseArgs({options:{'corner-file':{type:'string'}}}).values;
const tolerance=1e-6;
function near(a,b,msg) {assert.ok(Math.abs(a-b)<tolerance,`${msg}: ${a} / ${b}`);}
const hash=bytes=>createHash('sha256').update(bytes).digest('hex');
const ray=new THREE.Raycaster();
function first(o,origin,direction) {
  ray.set(new THREE.Vector3(...origin),new THREE.Vector3(...direction));
  return ray.intersectObject(o,true)[0];
}
const top=(o,x,z)=>first(o,[x,.2,z],[0,-1,0]);
const bottom=(o,x,z)=>first(o,[x,-.2,z],[0,1,0]);
function place(scene,x,y,z,rotation=0) {
  const copy=scene.clone(true);copy.position.set(x,y,z);copy.rotation.y=rotation;copy.updateMatrixWorld(true);
  return copy;
}
function bounds(o) {
  const box=new THREE.Box3().setFromObject(o,true);
  return [box.min.toArray(),box.max.toArray()];
}
function auditDiagonal(scene) {
  let count=0, caps=0, crossed=0;
  const v=new THREE.Vector3();
  scene.traverse(o=>{
    if(!o.isMesh)return;
    const pos=o.geometry.attributes.position,index=o.geometry.index;
    const n=index?index.count:pos.count;
    for(let i=0;i<n;i+=3) {
      const sides=[0,1,2].map(j=>{
        v.fromBufferAttribute(pos,index?index.getX(i+j):i+j).applyMatrix4(o.matrixWorld);
        return v.x-v.z;
      });
      if(sides.every(x=>Math.abs(x)<tolerance))caps++;
      if(sides.some(x=>x>tolerance)&&sides.some(x=>x< -tolerance))crossed++;
      count++;
    }
  });
  assert.equal(caps,0);assert.equal(crossed,0);
  return {trianglesChecked:count,internalCapTriangles:caps,crossingTriangles:crossed};
}
const expectedSide=[[-.003,.060],[-.008,.0585],[-.014,.0595],[-.04,.0575],[-.084,.0545],[-.095,.057]];
function side(o,arm,station,height) {
  return arm==='front' ? first(o,[station,height,3],[0,0,-1])?.point.z:
    first(o,[3,height,station],[-1,0,0])?.point.x;
}
function examineJoints(pair,straight) {
  const west=place(straight,-2,0,1.03);
  const south=place(straight,1.03,0,-2,Math.PI/2);
  let hits=0,maxStep=0;
  for (const [arm,external] of [['front',west],['right',south]]) {
    for(const offset of [.0005,.004,.016]) {
      const stations=[-1+offset,-1-offset];
      for(const radius of [.0003,.014,.0447,.058,.0598]) {
        const both=[pair,external].map((o,i)=>{
          const coords=arm==='front'?[stations[i],1+radius]:[1+radius,stations[i]];
          const height=top(o,...coords)?.point.y;near(height,0,'flat cap');
          return height;
        });
        maxStep=Math.max(maxStep,Math.abs(both[1]-both[0]));hits+=2;
      }
      for(const [height,rad] of expectedSide) {
        const firstDepth=side(pair,arm,stations[0],height);
        const secondDepth=side(external,arm,stations[1],height);
        near(firstDepth,1+rad,'corner fascia');near(secondDepth,1+rad,'straight fascia');
        maxStep=Math.max(maxStep,Math.abs(secondDepth-firstDepth));hits+=2;
      }
      for(const radius of [.002,.03,.054]) {
        for(const [i,o] of [pair,external].entries()){
          const coords=arm==='front'?[stations[i],1+radius]:[1+radius,stations[i]];
          near(bottom(o,...coords)?.point.y,-.1,'full depth');hits++;
        }
      }
    }
  }
  const a=bounds(pair), b=bounds(west),c=bounds(south);
  const endGapsM=[a[0][0]-b[1][0],a[0][2]-c[1][2]];
  endGapsM.forEach(g=>near(g,0,'end gap'));
  return {topSoffitAndFasciaHits:hits,maximumPairedStepM:maxStep,endGapsM};
}

function installed(tile,trim) {
  let hits=0;
  for(const station of [-.995,-.65,-.253,.004,.234,.501,.931,.995]) {
    for(const arm of ['front','right']) {
      for(const sign of [-1,1]) {
        const r=1+sign*.0003;
        const coords=arm==='front'?[station,r]:[r,station];
        near(top(sign<0?tile:trim,...coords)?.point.y,0,'tile to trim top');hits++;
      }
      for(const depth of [-.008,-.042,-.091]) {
        const tileRad=side(tile,arm,station,depth);
        near(tileRad,1,'slab face');
        const trimBack=arm==='front'?first(trim,[station,depth,.5],[0,0,1])?.point.z:
          first(trim,[.5,depth,station],[1,0,0])?.point.x;
        near(trimBack,tileRad,'slab to trim interface');hits+=2;
      }
    }
  }
  return hits;
}
const data={toleranceM:tolerance,forms:{},joins:[],tileContacts:[]};
const assets={Straight:[],Mitre:[]};
for(const form of ['Straight','Mitre']) {
  for(const i of [0,1,2]) {
    const name='mall-floor-edge-2m'+(form==='Mitre'?'-mitre':'')+(i?'-lod'+i:'')+'.glb';
    const {scene,bytes,json}=await readGlb(resolve(base,'exports',name));
    const result=await validateBytes(bytes,{uri:name,maxIssues:100});
    assert.equal(result.issues.numErrors,0,JSON.stringify(result.issues.messages));assert.equal(result.issues.numWarnings,0);
    const extras=[];
    JSON.stringify(json,(k,v)=>{if(k==='extras') extras.push(v);return v;});
    assert.deepEqual(extras,[{kit:'Full-depth 2 m mall floor edge',form,width_m:.06,depth_m:.1}]);
    assert.equal(json.buffers[0].uri,undefined);assert.equal(json.cameras,undefined);assert.equal(json.animations,undefined);
    assert.equal(json.images,undefined);
    const dims=bounds(scene);
    const expected=form==='Straight'?[[-1,-.1,-.03],[1,0,.03]]:[[-1,-.1,-1],[1.06,0,1.06]];
    dims.forEach((row,r)=>row.forEach((n,c)=>near(n,expected[r][c],'bounds')));
    const sockets=form==='Straight'?[['West',[-1,0,0]],['East',[1,0,0]]]:[['West',[-1,0,1.03]],['South',[1.03,0,-1]]];
    for(const [label,coords] of sockets) {
      const o=scene.getObjectByName('CONNECTOR_'+form+'_'+label+'_LOD'+i);assert.ok(o);
      o.getWorldPosition(new THREE.Vector3()).toArray().forEach((n,axis)=>near(n,coords[axis],'connector'));
    }
    const primitives=json.meshes.flatMap(m=>m.primitives);
    const row={file:name,sha256:hash(bytes),bytes:bytes.length,
      triangles:primitives.reduce((n,p)=>n+json.accessors[p.indices].count/3,0),draws:primitives.length,
      gltfBoundsM:dims,validator:{errors:0,warnings:0}};
    if(form==='Mitre') {
      row.diagonal=auditDiagonal(scene);
      let hits=0;
      for(const rad of [.001,.02,.04475,.055,.0595]) {
        for(const skew of [-.0003,.0003]){
          near(top(scene,1+rad,1+rad+skew)?.point.y,0,'diagonal top');hits++;
        }
      }
      for(const [height,radius] of expectedSide) {
        for(const skew of [-.0002,.0002]){
          const n=Math.SQRT1_2;
          const p=first(scene,[1.2+skew,height,1.2],[-n,0,-n])?.point;
          assert.ok(p,'outer corner closed');near(Math.max(p.x,p.z),1+radius,'diagonal fascia');hits++;
        }
      }
      row.diagonal.rayHits=hits;
    } else if(i<2) {
      const gold=top(scene,0,-.02)?.object.material.name;
      const stripe=top(scene,0,.01475)?.object.material.name;
      assert.equal(gold,'Satin champagne nosing');assert.equal(stripe,'Anodized bronze fascia');
    } else {
      assert.ok(primitives.every(p=>p.attributes.COLOR_0!==undefined));
    }
    data.forms[form+'LOD'+i]=row;assets[form].push(scene);
  }
  const [a,b,c]=[0,1,2].map(i=>data.forms[form+'LOD'+i]);
  assert.ok(a.triangles>b.triangles && b.triangles>c.triangles && a.bytes>b.bytes && b.bytes>c.bytes && c.draws<a.draws);
}
for(const m of [0,1,2])for(const s of [0,1,2]) {
  data.joins.push({mitreLOD:m,straightLOD:s,...examineJoints(assets.Mitre[m],assets.Straight[s])});
}
const floors=['models/mall-floor-module-2m/exports/mall-floor-module-2m.glb'];
floors.push(args['corner-file'] ?? 'models/mall-floor-corner-2m/exports/mall-floor-corner-2m.glb');
for(const file of floors) {
  const {scene,bytes}=await readGlb(resolve(file));
  const tile=place(scene,0,-.1,0);
  const counts=assets.Mitre.map(trim=>installed(tile,trim));
  data.tileContacts.push({tile:file.split('/').at(-1),sha256:hash(bytes),surfaceHitsPerLOD:counts});
}
const shifted=place(assets.Straight[0],-2.005,0,1.03);
assert.equal(top(shifted,-1.0025,1.03),undefined);assert.equal(top(assets.Mitre[0],-1.0025,1.03),undefined);
const old=await readGlb(resolve('models/mall-floor-edge-trim/exports/mall-floor-edge-trim.glb'));
assert.ok(bounds(old.scene)[0][1]>-.031);
assert.equal(first(old.scene,[0,-.085,1],[0,0,-1]),undefined);
data.controls=['5 mm straight displacement leaves a through gap','Legacy 30 mm trim leaves the lower fascia exposed'];
data.result='pass';
await fs.mkdir(resolve(base,'reports'),{recursive:true});
await fs.writeFile(resolve(base,'reports/assembly.json'),JSON.stringify(data,null,2)+'\n');
console.log(JSON.stringify(data));

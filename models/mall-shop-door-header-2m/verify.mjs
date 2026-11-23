// Verify the actual stepped fascia above the unscaled existing door and wall returns.
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import fs from 'node:fs/promises';
import {createRequire} from 'node:module';
import {dirname,resolve} from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
const base=dirname(fileURLToPath(import.meta.url)),project=createRequire(resolve('package.json'));
const T=await import(new URL('three.module.js',pathToFileURL(project.resolve('three'))).href);
const {readGlb}=await import(pathToFileURL(resolve('models/mall-floor-tile/glb.mjs')).href);
const {validateBytes}=project('gltf-validator');
const sha=b=>createHash('sha256').update(b).digest('hex'),tol=1e-6;
const near=(a,b,why)=>assert.ok(Math.abs(a-b)<tol,`${why}: ${a} / ${b}`);
function place(scene,x,y,z,yaw=0){const c=scene.clone(true);c.position.set(x,y,z);c.rotation.y=yaw;c.updateMatrixWorld(true);return c;}
const box=o=>new T.Box3().setFromObject(o,true);
const ray=new T.Raycaster();
function hit(model,xyz,dir){ray.set(new T.Vector3(...xyz),new T.Vector3(...dir));return ray.intersectObject(model,true)[0]?.point;}
const doorIn=await readGlb(resolve('models/mall-shopfront-door/exports/mall-shopfront-door.glb'));
const cornerIn=await readGlb(resolve('models/mall-wall-corner-2m/exports/mall-wall-corner-2m.glb'));
const door=place(doorIn.scene,0,0,3.135),left=place(cornerIn.scene,-3,0,3,Math.PI),right=place(cornerIn.scene,3,0,3,-Math.PI/2);
const fixed=door.getObjectByName('FRAME_Header'),hinges=['HINGE_Left','HINGE_Right'].map(n=>door.getObjectByName(n));
assert.ok(fixed&&hinges.every(Boolean));

function fit(header) {
  let frameSamples=0,wallSamples=0,stepSamples=0;
  let worstGap=0,lowestSweepClearance=Infinity,openPassage=0;
  for(const x of [-1.045,-1.025,-.995,-.75,0,.75,.995,1.025,1.045]) {
    for(const depth of [3.078,3.095,3.135,3.177,3.192]) {
      const top=hit(fixed,[x,2.65,depth],[0,-1,0]);
      const soffit=hit(header,[x,2.25,depth],[0,1,0]);
      near(top?.y,2.4,'frame head');near(soffit?.y,top.y,'frame seat');
      worstGap=Math.max(worstGap,Math.abs(soffit.y-top.y));frameSamples+=2;
    }
  }
  for(const [sign,wall] of [[-1,left],[1,right]]) {
    for(const h of [2.42,2.48,2.65,2.77]) {
      for(const z of [2.946,2.98,3.03,3.069]) {
        const w=hit(wall,[0,h,z],[sign,0,0]);
        const edge=hit(header,[1.4*sign,h,z],[-sign,0,0]);
        near(w?.x,sign,'wall end on rear fill');near(edge?.x,w.x,'rear fill end');
        worstGap=Math.max(worstGap,Math.abs(w.x-edge.x));wallSamples+=2;
      }
      for(const outward of [.007,.028,.045]) {
        const x=sign*(1+outward);
        const wallFace=hit(wall,[x,h,3.45],[0,0,-1]);
        const earBack=hit(header,[x,h,2.99],[0,0,1]);
        near(wallFace?.z,3.075,'wall outer plane');near(earBack?.z,wallFace.z,'50 mm outside lap');
        worstGap=Math.max(worstGap,Math.abs(earBack.z-wallFace.z));wallSamples+=2;
      }
    }
    for(const x of [.985,1.018,1.043]) {
      const under=hit(header,[sign*x,2.3,3.04],[0,1,0]);
      if(x<1)near(under?.y,2.4,'rear head underside');else assert.equal(under,undefined,'rear infill must stop at opening width');
      const over=hit(header,[sign*x,3.1,3.12],[0,-1,0]);near(over?.y,2.8,'top of stepped face');stepSamples+=2;
    }
  }
  const low=box(header).min.y;
  for(let degrees=0;degrees<=90;degrees++){
    hinges[0].rotation.y= -degrees*Math.PI/180;hinges[1].rotation.y=degrees*Math.PI/180;door.updateMatrixWorld(true);
    const bounds=hinges.map(box);
    for(const arm of bounds)lowestSweepClearance=Math.min(lowestSweepClearance,low-arm.max.y);
    if(degrees===90)openPassage=bounds[1].min.x-bounds[0].max.x;
  }
  for(const h of hinges)h.rotation.y=0;door.updateMatrixWorld(true);
  near(lowestSweepClearance,.1,'swing clearance');assert.ok(openPassage>1.73 && openPassage<1.75);
  return {fixedHeadAndSoffitHits:frameSamples,wallInterfacesHits:wallSamples,stepAndTopChecks:stepSamples,
    maximumMatingPlaneGapM:worstGap,sampledHingeAngles:91,minimumVerticalLeafClearanceM:lowestSweepClearance,
    fullOpenClearWidthM:openPassage};
}
const report={toleranceM:tol,doorSha256:sha(doorIn.bytes),wallCornerSha256:sha(cornerIn.bytes),levels:{}};
let positive;
for(const i of [0,1,2]){
  const name='mall-shop-door-header-2m'+(i?'-lod'+i:'')+'.glb';
  const {bytes,scene,json}=await readGlb(resolve(base,'exports',name));
  const validation=await validateBytes(bytes,{uri:name,maxIssues:100});
  assert.equal(validation.issues.numErrors,0,JSON.stringify(validation.issues.messages));assert.equal(validation.issues.numWarnings,0);
  const extras=[];JSON.stringify(json,(k,v)=>{if(k==='extras')extras.push(v);return v;});
  assert.deepEqual(extras,[{opening_m:2,height_m:.4,front:'glTF +Z'}]);
  assert.equal(json.buffers[0].uri,undefined);assert.equal(json.animations,undefined);assert.equal(json.cameras,undefined);
  assert.equal(json.images?.length||0,i===0?1:0);
  const b=box(scene);
  [[b.min,[-1.05,0,-.075]],[b.max,[1.05,.4,.195]]].forEach(([pt,expected])=>pt.toArray().forEach((k,j)=>near(k,expected[j],'bounds')));
  for(const [label,expected] of [['West',[-1,0,0]],['East',[1,0,0]],['DoorTop',[0,0,.135]]]){
    const obj=scene.getObjectByName('CONNECTOR_'+label+'_LOD'+i);assert.ok(obj);obj.getWorldPosition(new T.Vector3()).toArray().forEach((n,j)=>near(n,expected[j],'connector'));
  }
  const prims=json.meshes.flatMap(m=>m.primitives);
  const installed=place(scene,0,2.4,3);
  const meshes={triangles:prims.reduce((s,p)=>s+json.accessors[p.indices].count/3,0),draws:prims.length};
  const row={file:name,bytes:bytes.length,sha256:sha(bytes),...meshes,validator:{errors:0,warnings:0},geometry:fit(installed)};
  if(i){
    const prev=report.levels['LOD'+(i-1)];assert.ok(row.triangles<prev.triangles && row.draws<prev.draws && row.bytes<prev.bytes);
  } else positive=scene;
  report.levels['LOD'+i]=row;
}
const raised=place(positive,0,2.405,3);
assert.throws(()=>fit(raised),/frame seat/);
const intoOpening=place(positive,0,2.4,2.99);
assert.throws(()=>fit(intoOpening),/frame seat/);
report.negativeControls=['Raising the header by 5 mm opens the frame seat','Moving it inward 10 mm uncovers the outer frame seat'];
report.result='pass';
await fs.mkdir(resolve(base,'reports'),{recursive:true});
await fs.writeFile(resolve(base,'reports/geometry.json'),JSON.stringify(report,null,2)+'\n');
console.log(JSON.stringify(report));

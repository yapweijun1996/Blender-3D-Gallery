// Run from the gallery root. Probe the actual corner and both adjoining straight modules.
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import fs from 'node:fs/promises';
import { createRequire } from 'node:module';
import { dirname, resolve } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { parseArgs } from 'node:util';

const asset = dirname(fileURLToPath(import.meta.url));
const { values } = parseArgs({options:{'straight-dir':{type:'string'}}});
const straightDir=values['straight-dir'] || resolve(asset,'../mall-wall-module-2m');
const project = createRequire(resolve('package.json'));
const THREE = await import(new URL('three.module.js',pathToFileURL(project.resolve('three'))).href);
const {readGlb}=await import(pathToFileURL(resolve('models/mall-floor-tile/glb.mjs')).href);
const {validateBytes}=project('gltf-validator');
const tolerance=1e-6;
const sha=bytes=>createHash('sha256').update(bytes).digest('hex');
const ray=new THREE.Raycaster();
function near(a,b,where) {assert.ok(Math.abs(a-b)<tolerance,`${where}: got ${a}, expected ${b}`);}

function placed(scene,x,z,a=0) {
  const copy=scene.clone(true);
  copy.position.set(x,0,z);copy.rotation.y=a;copy.updateMatrixWorld(true);
  return copy;
}

function hit(model, origin, direction) {
  ray.set(new THREE.Vector3(...origin),new THREE.Vector3(...direction).normalize());
  return ray.intersectObject(model,true)[0]?.point;
}

function face(model, arm, side, offset, height, back) {
  const start=back?-1:1;
  if (arm==='x') {
    return hit(model,[-2+side*offset,height,start],[0,0,-start])?.z;
  }
  const p=hit(model,[-start,height,2-side*offset],[start,0,0]);
  return p ? -p.x : undefined;
}

function outerConnections(corner, straight, cornerLevel, straightLevel) {
  const west=placed(straight,-3,0), turn=placed(straight,0,3,-Math.PI/2);
  const cb=new THREE.Box3().setFromObject(corner,true);
  const westBox=new THREE.Box3().setFromObject(west,true);
  const turnBox=new THREE.Box3().setFromObject(turn,true);
  const gapsM=[cb.min.x-westBox.max.x,turnBox.min.z-cb.max.z];
  gapsM.forEach(gap=>near(gap,0,'terminal gap'));
  let hits=0,largestFlushDifference=0;
  for(const [arm,external] of [['x',west],['z',turn]]) {
    for(const offset of [.0005,.004,.017]) {
      for(const [height,regular] of [[.06,.075],[.11,.075],[.65,.072],[1.94,.072],[2.77,.075]]) {
        let paired=[];
        for(const [model,side,level] of [[corner,1,cornerLevel],[external,-1,straightLevel]]) {
          const expected=level<2 && regular===.072 && offset<.002 ? .062 : regular;
          const front=face(model,arm,side,offset,height,false);
          near(front,expected,'terminal front');
          near(face(model,arm,side,offset,height,true),-.075,'terminal rear');
          paired.push(front);hits+=2;
        }
        if (offset>=.004) largestFlushDifference=Math.max(largestFlushDifference,Math.abs(paired[1]-paired[0]));
      }
    }
  }
  near(largestFlushDifference,0,'flush face outside reveal');
  return {gapsM,frontAndRearHits:hits,largestFlushDifferenceM:largestFlushDifference};
}

function insideTurn(scene,level) {
  let hits=0;
  for(const [h,front] of [[.06,.075],[.65,level===2?.072:.062],[1.9,level===2?.072:.062],[2.77,.075]]) {
    // A small offset from the exact crease independently tests both triangles.
    for(const skew of [-.0002,.0002]) {
      const inside=hit(scene,[-.3+skew,h,.3],[1,0,-1]);
      const outside=hit(scene,[.3+skew,h,-.3],[-1,0,1]);
      assert.ok(inside && outside,'both miter faces must exist');
      near(Math.max(-inside.x,inside.z),front+Math.abs(skew),'interior crease');
      near(Math.max(outside.x,-outside.z),.075,'exterior crease');
      hits+=2;
    }
  }
  // At 20 mm from the elbow the front returns to the authored stone surface.
  const left=hit(scene,[-.097,.65,.3],[0,0,-1]);
  const returning=hit(scene,[-.3,.65,.097],[1,0,0]);
  near(left?.z,.072,'stone on X arm');near(-returning?.x,.072,'stone on Z arm');
  return hits+2;
}

function miterAudit(scene) {
  let sectionCrossings=0,internalCaps=0,largestThinDimension=0;
  const vertices=[new THREE.Vector3(),new THREE.Vector3(),new THREE.Vector3()];
  scene.traverse(o=>{
    if (!o.isMesh) return;
    // Native mall collision uses one planar box per Three mesh. A bent mesh
    // would enclose the aisle even with a visually perfect diagonal.
    const size=new THREE.Box3().setFromObject(o,true).getSize(new THREE.Vector3());
    const thin=Math.min(size.x,size.z);
    assert.ok(thin<=.150001, 'broad collision box for '+o.name);
    largestThinDimension=Math.max(largestThinDimension,thin);
    const p=o.geometry.attributes.position, index=o.geometry.index;
    const count=index?index.count:p.count;
    for(let i=0;i<count;i+=3) {
      const signed=vertices.map((v,j)=>{
        v.fromBufferAttribute(p,index?index.getX(i+j):i+j).applyMatrix4(o.matrixWorld);
        return v.x+v.z;
      });
      if(signed.every(s=>Math.abs(s)<tolerance)) internalCaps++;
      if(signed.some(s=>s>tolerance) && signed.some(s=>s< -tolerance)) sectionCrossings++;
    }
  });
  assert.equal(internalCaps,0,'interior miter retained a coplanar end cap');
  assert.equal(sectionCrossings,0,'faces from one arm extend across the miter');
  return {interiorCapTriangles:internalCaps,crossingTriangles:sectionCrossings,largestThinArmExtentM:largestThinDimension};
}

const report={toleranceM:tolerance,levels:{},straightConnections:[]};
const corners=[],straights=[];
for(const level of [0,1,2]){
  const suffix=level===0?'':'-lod'+level;
  const file='mall-wall-corner-2m'+suffix+'.glb';
  const wallFile='mall-wall-module-2m'+suffix+'.glb';
  const corner=await readGlb(resolve(asset,'exports',file));
  const straight=await readGlb(resolve(straightDir,'exports',wallFile));
  corners.push(corner.scene);straights.push(straight.scene);
  const val=await validateBytes(corner.bytes,{uri:file,maxIssues:100});
  assert.equal(val.issues.numErrors,0,JSON.stringify(val.issues.messages));
  assert.equal(val.issues.numWarnings,0,JSON.stringify(val.issues.messages));
  const extras=[];
  JSON.stringify(corner.json,(k,v)=>{if(k==='extras') extras.push(v);return v;});
  assert.deepEqual(extras,[{backlog_id:'MALL-STR-011',arm_m:2,front:'Interior glTF +Z on the X arm and -X on the Z arm.'}]);
  assert.equal(corner.json.buffers[0].uri,undefined);
  assert.equal(corner.json.cameras,undefined);assert.equal(corner.json.animations,undefined);
  assert.equal(corner.json.images?.length||0,level===0?1:0);
  const bounds=new THREE.Box3().setFromObject(corner.scene,true);
  for(const [actual,expected] of [[bounds.min,[-2,0,-.075]],[bounds.max,[.075,2.8,2]]]) {
    actual.toArray().forEach((n,i)=>near(n,expected[i],'corner envelope'));
  }
  for(const [name,coords] of [['Left',[-2,0,0]],['Return',[0,0,2]]]) {
    const obj=corner.scene.getObjectByName('CONNECTOR_'+name+'_LOD'+level);
    assert.ok(obj);
    obj.getWorldPosition(new THREE.Vector3()).toArray().forEach((n,i)=>near(n,coords[i],'end socket'));
  }
  const primitives=corner.json.meshes.flatMap(m=>m.primitives);
  const triangles=primitives.reduce((n,p)=>n+corner.json.accessors[p.indices].count/3,0);
  const stats={sha256:sha(corner.bytes),straightSha256:sha(straight.bytes),bytes:corner.bytes.length,
    triangles,draws:primitives.length,bounds:{min:bounds.min.toArray(),max:bounds.max.toArray()},
    validator:{errors:0,warnings:0},miterFaceAudit:miterAudit(corner.scene),diagonalAndPanelHits:insideTurn(corner.scene,level)};
  if(level) {
    const previous=report.levels['LOD'+(level-1)];
    assert.ok(triangles<previous.triangles && stats.draws<previous.draws && stats.bytes<previous.bytes);
  }
  report.levels['LOD'+level]=stats;
}
for(const c of [0,1,2]) for(const s of [0,1,2]) {
  report.straightConnections.push({cornerLevel:c,straightLevel:s,...outerConnections(corners[c],straights[s],c,s)});
}
const flipped=placed(straights[0],0,3,Math.PI/2);
const flippedFace=hit(flipped,[-1,.65,2.04],[1,0,0]);
assert.ok(flippedFace && Math.abs(-flippedFace.x-.072)>.002);
const shifted=placed(straights[0],0,3.005,-Math.PI/2);
assert.equal(hit(shifted,[-1,.65,2.0025],[1,0,0]),undefined);
assert.equal(hit(corners[0],[-1,.65,2.0025],[1,0,0]),undefined);
report.negativeControls=['Reversed public face of a return straight','Return straight displaced 5 mm along its run'];
report.result='pass';
await fs.mkdir(resolve(asset,'reports'),{recursive:true});
await fs.writeFile(resolve(asset,'reports/geometry.json'),JSON.stringify(report,null,2)+'\n');
console.log(JSON.stringify(report));

import assert from 'node:assert/strict';
import fs from 'node:fs';
import crypto from 'node:crypto';
import { Box3, Vector3, Raycaster } from 'three';
import { validateBytes } from 'gltf-validator';
import { readGlb } from '../mall-floor-tile/glb.mjs';
const root=new URL('../../',import.meta.url);
const refs={floor:'models/mall-floor-tile/exports/mall-floor-tile-module.glb',edge:'models/mall-floor-edge-trim/exports/mall-floor-edge-trim.glb',cap:'models/mall-floor-corner-trim/exports/mall-floor-corner-trim.glb',wall:'models/mall-solid-wall/exports/mall-solid-wall.glb',corner:'models/mall-wall-corner/exports/mall-wall-corner.glb'};
const inputs={};for(const [id,path] of Object.entries(refs)) inputs[id]=await readGlb(new URL(path,root).pathname);
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
const near=(a,b,t=1e-6)=>assert.ok(Math.abs(a-b)<t,`${a} != ${b}`);
const box=(o)=>{o.updateMatrixWorld(true);return new Box3().setFromObject(o)};
function placed(scene,x,y,z,rotation=0){const o=scene.clone(true);o.position.set(x,y,z);o.rotation.y=rotation;o.updateMatrixWorld(true);return o}
const reports={};
for (const [id,node,dim] of [['cap','ASSET_MallFloorCornerTrim',[.06,.03,.06]],['corner','ASSET_MallWallCorner',[1.26,3,1.26]]]) {
 const data=inputs[id]; const result=await validateBytes(new Uint8Array(data.bytes),{uri:`${id}.glb`});
 assert.equal(result.issues.numErrors,0,`${id} glTF errors`);assert.equal(result.issues.numWarnings,0,`${id} glTF warnings`);
 assert.ok(![...(data.json.buffers??[]),...(data.json.images??[])].some(a=>a.uri));assert.ok(!data.json.cameras?.length&&!data.json.animations?.length);
 assert.ok(data.scene.getObjectByName(node));const bb=box(data.scene),size=bb.getSize(new Vector3());for(let i=0;i<3;i++)near(size.getComponent(i),dim[i]);
 let triangles=0;for(const mesh of data.json.meshes??[])for(const p of mesh.primitives)triangles+=(p.indices===undefined?data.json.accessors[p.attributes.POSITION].count:data.json.accessors[p.indices].count)/3;
 reports[id]={sha256:sha(data.bytes),bytes:data.bytes.length,triangles,materials:data.json.materials.length,bounds:{min:bb.min.toArray(),max:bb.max.toArray()},dimensions:size.toArray(),validator:{errors:result.issues.numErrors,warnings:result.issues.numWarnings,infos:result.issues.numInfos}};
}
// An external floor corner: two existing strips surround the tile; cap fills the 60 mm square.
const tile=placed(inputs.floor.scene,0,-.03,0), stripX=placed(inputs.edge.scene,0,0,.63),stripZ=placed(inputs.edge.scene,.63,0,0,Math.PI/2),cap=placed(inputs.cap.scene,.63,0,.63);
const [tf,tx,tz,tc]=[tile,stripX,stripZ,cap].map(box);
near(tf.max.y,0);near(tx.max.y,0);near(tz.max.y,0);near(tc.max.y,0);
near(tf.max.z,tx.min.z);near(tf.max.x,tz.min.x);near(tx.max.x,tc.min.x);near(tz.max.z,tc.min.z);near(tx.min.z,tc.min.z);near(tz.min.x,tc.min.x);
// Probe visible top surfaces close to each of the two cap seams.
const floorParts=[stripX,stripZ,cap];let floorHits=0;
for(const [x,z] of [[.599,.63],[.601,.63],[.63,.599],[.63,.601],[.63,.63]]){
 const hit=new Raycaster(new Vector3(x,1,z),new Vector3(0,-1,0)).intersectObjects(floorParts,true)[0];assert.ok(hit,`missing top surface at ${x},${z}`);near(hit.point.y,0);floorHits++;
}
// Corner's centreline ends connect to two actual 1.2 m straight-wall GLBs.
const corner=placed(inputs.corner.scene,0,0,0),wallX=placed(inputs.wall.scene,-1.8,0,0),wallZ=placed(inputs.wall.scene,0,0,1.8,-Math.PI/2);
const armX=corner.getObjectByName('ARM_X_Core'),armY=corner.getObjectByName('ARM_Y_Core');assert.ok(armX&&armY);
const [cx,cz,wx,wz]=[armX,armY,wallX,wallZ].map(box);
near(cx.min.x,wx.max.x);near(cz.max.z,wz.min.z);near(cx.min.y,0);near(cz.min.y,0);near(cx.max.y,3);near(cz.max.y,3);
const conX=corner.getObjectByName('CONNECTOR_X').getWorldPosition(new Vector3()),conY=corner.getObjectByName('CONNECTOR_Y').getWorldPosition(new Vector3());near(conX.x,-1.2);near(conY.z,1.2);
// Compare matching inside surfaces on either side of each connector, including the panel reveal.
const samples = [
  { offset: .001, height: 1.5, surface: /core/i },
  { offset: .006, height: 1.5, surface: /panel/i },
  { offset: .006, height: .06, surface: /base/i },
  { offset: .006, height: 2.96, surface: /top/i },
];
const wallFinishStepsMm = [];
for (const { offset, height, surface } of samples) {
  for (const [straightWall, cornerOrigin, wallOrigin, direction] of [
    [wallX, new Vector3(conX.x + offset, height, .4), new Vector3(conX.x - offset, height, .4), new Vector3(0, 0, -1)],
    [wallZ, new Vector3(-.4, height, conY.z - offset), new Vector3(-.4, height, conY.z + offset), new Vector3(1, 0, 0)],
  ]) {
    const cornerHit = new Raycaster(cornerOrigin, direction).intersectObject(corner, true)[0];
    const wallHit = new Raycaster(wallOrigin, direction).intersectObject(straightWall, true)[0];
    assert.match(cornerHit?.object.name ?? '', surface, 'corner inside surface');
    assert.match(wallHit?.object.name ?? '', surface, 'straight wall inside surface');
    near(cornerHit.distance, wallHit.distance);
    wallFinishStepsMm.push(Math.abs(cornerHit.distance - wallHit.distance) * 1000);
  }
}
const report={result:'PASS',inputs:Object.fromEntries(Object.entries(inputs).map(([id,v])=>[id,{path:refs[id],sha256:sha(v.bytes)}])),models:reports,floor:{tile:[0,-.03,0],stripX:[0,0,.63],stripZ:[.63,0,0],corner:[.63,0,.63],topSurfaceRayHits:floorHits},wall:{corner:[0,0,0],straightX:[-1.8,0,0],straightZ:[0,0,1.8],straightZRotationRadians:wallZ.rotation.y,connectors:[conX.toArray(),conY.toArray()],insideFinishedFaces:2,finishSamplePairs:wallFinishStepsMm.length,maxFinishStepMm:Math.max(...wallFinishStepsMm)},limits:'Specific 90-degree case, bounding boxes and sample rays only. Does not establish arbitrary layouts, triangle intersection, materials under all renderers, physical safety, or building certification.'};
for(const id of ['mall-floor-corner-trim','mall-wall-corner'])fs.writeFileSync(new URL(`models/${id}/reports/corner-validation.json`,root),JSON.stringify(report,null,2)+'\n');
console.log(JSON.stringify(report));

import fs from 'node:fs';
import {createHash} from 'node:crypto';
import assert from 'node:assert/strict';
import {Box3,Vector3,Raycaster} from 'three';
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';
import validator from 'gltf-validator';
export const dir=new URL('.',import.meta.url),id='mall-food-court-tray-station',sha=b=>createHash('sha256').update(b).digest('hex');
export async function readGlb(file){const bytes=fs.readFileSync(file),json=JSON.parse(bytes.subarray(20,20+bytes.readUInt32LE(12))),gltf=await new GLTFLoader().parseAsync(bytes.buffer.slice(bytes.byteOffset,bytes.byteOffset+bytes.byteLength),'');gltf.scene.updateMatrixWorld(true);return {bytes,json,scene:gltf.scene};}
const a=await readGlb(new URL('exports/optimized.glb',dir)),v=await validator.validateBytes(new Uint8Array(a.bytes));
assert.equal(v.issues.numErrors,0);assert.equal(v.issues.numWarnings,0);assert.equal(a.json.images?.length||0,0);assert.ok(a.json.buffers.every(b=>!b.uri));
export const groups=['CabinetLeft','CabinetRight','CabinetBack','LowerShelf','UpperShelf','Counter','Feet','SignFrame','SignText','Tray01','Tray02','Tray03','Tray04'];
const root=a.scene.getObjectByName('ASSET_MallFoodCourtTrayStation');
const boxes=Object.fromEntries(groups.map(name=>{const o=a.scene.getObjectByName(name);assert.equal(o?.parent,root);let mesh=false;o.traverse(c=>mesh||=!!c.isMesh);assert.ok(mesh);return [name,new Box3().setFromObject(o)];}));
const b=new Box3().setFromObject(a.scene),dimensions=b.getSize(new Vector3()).toArray();
for(const [i,x] of [1.5,1.49,.66].entries())assert.ok(Math.abs(dimensions[i]-x)<1e-6,JSON.stringify(dimensions));assert.ok(Math.abs(b.min.y)<1e-6);
let triangles=0,vertices=0,primitives=0;const nodes=[];a.scene.traverse(o=>{nodes.push(o.name);if(o.isMesh){primitives++;vertices+=o.geometry.attributes.position.count;triangles+=(o.geometry.index?.count??o.geometry.attributes.position.count)/3;}});
assert.ok(a.bytes.length<600000&&triangles<12000&&primitives<=18,JSON.stringify({bytes:a.bytes.length,triangles,primitives}));
const near=(a,b)=>assert.ok(Math.abs(a-b)<1e-6,`${a} != ${b}`);
near(boxes.Counter.min.y,boxes.CabinetLeft.max.y);near(boxes.Counter.min.y,boxes.CabinetRight.max.y);
near(boxes.CabinetRight.min.x-boxes.CabinetLeft.max.x,1.36);
near(boxes.UpperShelf.min.y-boxes.LowerShelf.max.y,.33);near(boxes.Counter.min.y-boxes.UpperShelf.max.y,.33);
const apertures=[];
for(const y of [.40,.75]){
 const ray=new Raycaster(new Vector3(0,y,2),new Vector3(0,0,-1));const hits=ray.intersectObject(root,true);assert.ok(hits.length);assert.ok(hits[0].object.name.startsWith('CabinetBack'));near(hits[0].point.z,-.28);apertures.push({height_m:y,firstHit:hits[0].object.name,depth_glTF_z_m:hits[0].point.z});
}
const trayChecks=[];
for(const [i,name] of ['Tray01','Tray02','Tray03','Tray04'].entries()){
 const t=boxes[name],d=t.getSize(new Vector3());for(const [j,x] of [.45,.03,.33].entries())near(d.toArray()[j],x);
 assert.ok(t.min.x>boxes.CabinetLeft.max.x&&t.max.x<boxes.CabinetRight.min.x&&t.min.z>boxes.CabinetBack.max.z);
 // Downward ray at the centre must enter the hollow bowl and hit its 6 mm floor.
 const center=t.getCenter(new Vector3()),hits=new Raycaster(new Vector3(center.x,t.max.y+.1,center.z),new Vector3(0,-1,0)).intersectObject(root.getObjectByName(name),true);
 assert.ok(hits.length);near(hits[0].point.y-t.min.y,.006);
 const shelf=i<3?boxes.LowerShelf:boxes.UpperShelf;assert.ok(t.min.y-shelf.max.y>.0029);
 trayChecks.push({name,dimensions_m:d.toArray(),hollowFloorThickness_m:hits[0].point.y-t.min.y,bottom_m:t.min.y});
}
for(const [low,high] of [['Tray01','Tray02'],['Tray02','Tray03']])near(boxes[high].min.y-boxes[low].max.y,.005);
// Sweep the independently editable upper tray straight forward 0.62 m.
const swept=boxes.Tray04.clone();swept.max.z+=.62;
for(const name of groups.filter(n=>!n.startsWith('Tray')))assert.ok(!swept.intersectsBox(boxes[name]),'tray removal collision: '+name);
const removed=boxes.Tray04.clone().translate(new Vector3(0,0,.62));assert.ok(removed.min.z>boxes.Counter.max.z);
export const report={id,sha256:sha(a.bytes),glb_bytes:a.bytes.length,triangles,vertices,primitives,materials:a.json.materials.length,textures:0,animations:a.json.animations?.length||0,dimensions,bounds:{min:b.min.toArray(),max:b.max.toArray()},nodes,validation:{errors:v.issues.numErrors,warnings:v.issues.numWarnings,validator:v.validatorVersion}};
export const geometry={status:'PASS',units:'metres',dimensions_glTF_m:dimensions,floorPlane_glTF_Y_m:0,independentModules:groups,frontAxis:'Blender -Y / glTF +Z',clearOpeningWidth_m:1.36,shelfVerticalClearances_m:[.33,.33],apertureRays:apertures,trays:trayChecks,stackGap_m:.005,trayRemoval:{status:'PASS',distance_m:.62,minimumShelfGap_m:.003,sweptBoxNoFixedModuleCollision:true,fullyOutsideCounter:true},staticProp:true};
fs.writeFileSync(new URL('reports/assets.json',dir),JSON.stringify(report,null,2)+'\n');fs.writeFileSync(new URL('reports/geometry.json',dir),JSON.stringify(geometry,null,2)+'\n');console.log(JSON.stringify(report));

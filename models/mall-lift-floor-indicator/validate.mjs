import fs from 'node:fs';
import assert from 'node:assert/strict';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';
import {Box3,Vector3,Raycaster} from 'three';
import validator from 'gltf-validator';
import {readGlb,near} from './glb.mjs';
const dir=fileURLToPath(new URL('.',import.meta.url));
const {bytes,json,scene}=await readGlb(dir+'exports/optimized.glb');
const validation=await validator.validateBytes(new Uint8Array(bytes));
assert.equal(validation.issues.numErrors,0);assert.equal(validation.issues.numWarnings,0);
const root=scene.getObjectByName('ASSET_MallLiftFloorIndicator');assert.ok(root);assert.deepEqual(root.position.toArray(),[0,0,0]);
assert.equal(json.animations?.length||0,0);assert.equal(json.textures?.length||0,0);assert.ok(!json.cameras?.length&&!json.extensions?.KHR_lights_punctual);assert.ok(json.buffers.every(x=>!x.uri));
const parts={};let triangles=0,vertices=0,primitives=0;
scene.traverse(o=>{if(!o.isMesh)return;const a=o.geometry.attributes.position,idx=o.geometry.index,b=new Box3().setFromObject(o),t=(idx?.count??a.count)/3;assert.ok(t>0);for(let i=0;i<a.count;i++)for(const v of [a.getX(i),a.getY(i),a.getZ(i)])assert.ok(Number.isFinite(v));parts[o.name]={triangles:t,vertices:a.count,min:b.min.toArray(),max:b.max.toArray()};triangles+=t;vertices+=a.count;primitives++;});
assert.equal(primitives,20);assert.equal(json.materials.length,5);assert.ok(triangles<5000&&bytes.length<200*1024);
const b=new Box3().setFromObject(root),dims=b.getSize(new Vector3()).toArray();[.42,.16,.0268].forEach((v,i)=>near(dims[i],v));near(b.min.y,0);near(b.min.z,0);
const bezel=root.getObjectByName('MODULE_MetalBezel'),housing=root.getObjectByName('MODULE_Housing'),face=root.getObjectByName('MODULE_DarkFace');assert.ok(bezel&&housing&&face);
const measureRay=(o,x,y)=>{const saved=o.material.side;o.material.side=2;const hits=new Raycaster(new Vector3(x,y,.1),new Vector3(0,0,-1)).intersectObject(o,true);o.material.side=saved;return hits.map(x=>x.point.z).filter((v,i,a)=>i===0||Math.abs(v-a[i-1])>1e-6)};
const back=measureRay(housing,0,.08);assert.equal(back.length,2);near(Math.abs(back[0]-back[1]),.0015);
near(parts.MODULE_MetalBezel.max[2]-parts.MODULE_MetalBezel.min[2],.003);assert.equal(measureRay(bezel,0,.08).length,0,'open bezel aperture');assert.equal(measureRay(bezel,.202,.08).length,2);
const wall=root.getObjectByName('CONNECTOR_WallMount');wall.getWorldPosition(new Vector3()).toArray().forEach((v,i)=>near(v,[0,.08,0][i]));
assert.equal(root.userData.display_floor,'02');assert.equal(root.userData.display_direction,'up');
const digitChecks=[];
for(const [index,expected] of [[0,'abcdef'],[1,'abdeg']]){
 let active='';
 for(const segment of 'abcdefg'){
  const o=root.getObjectByName('SEGMENT_Digit'+index+'_'+segment);assert.ok(o);assert.equal(o.parent.name,'MODULE_Digit'+index);const on=o.material.emissiveIntensity>0&&o.material.emissive.r>0;
  assert.equal(on,expected.includes(segment));assert.equal(o.userData.illuminated,on);if(on)active+=segment;
  const pb=parts[o.name];assert.ok(pb.min[2]>=parts.MODULE_DarkFace.max[2]-1e-6);assert.ok(pb.min[0]>-.196&&pb.max[0]<.196&&pb.min[1]>.014&&pb.max[1]<.146);
 }
 assert.equal(active,expected);digitChecks.push({index,digit:'02'[index],activeSegments:active,independentMeshes:7});
}
for(const name of ['Shaft','Left','Right']){const o=root.getObjectByName('SEGMENT_Arrow_'+name);assert.ok(o);assert.equal(o.parent.name,'MODULE_Direction');assert.ok(o.material.emissive.r>0);}
assert.ok(!Object.keys(parts).some(n=>/Button|Call/.test(n)));
export const geometry={status:'PASS',units:'metres',width_m:dims[0],height_m:dims[1],depth_m:dims[2],housingWallThickness_m:.0015,bezelThickness_m:.003,wallAnchor:[0,.08,0],frontAxis:'glTF +Z / Blender -Y',digitChecks,independentArrowParts:3,display:'02 up',liveElevatorState:'NOT IMPLEMENTED',runtimeUpdate:'NOT IMPLEMENTED'};
export const report={id:'mall-lift-floor-indicator',sha256:createHash('sha256').update(bytes).digest('hex'),glb_bytes:bytes.length,triangles,vertices,primitives,materials:json.materials.length,textures:0,animations:0,dimensions:dims,bounds:{min:b.min.toArray(),max:b.max.toArray()},parts,validation:{errors:validation.issues.numErrors,warnings:validation.issues.numWarnings,validator:'2.0.0-dev.3.10'}};
fs.writeFileSync(dir+'reports/assets.json',JSON.stringify(report,null,2)+'\n');fs.writeFileSync(dir+'reports/geometry.json',JSON.stringify(geometry,null,2)+'\n');
console.log(JSON.stringify({sha256:report.sha256,glb_bytes:bytes.length,triangles,vertices,primitives,materials:report.materials,validation:report.validation,geometry:geometry.status}));

import assert from 'node:assert/strict';import fs from 'node:fs';import {fileURLToPath} from 'node:url';import {createHash} from 'node:crypto';
import {Box3,Vector3} from 'three';import {OBB} from 'three/addons/math/OBB.js';import validator from 'gltf-validator';import {readGlb,near} from './glb.mjs';
const root=fileURLToPath(new URL('.',import.meta.url));const {bytes,json,scene}=await readGlb(root+'exports/mall-shopfront-roller-shutter.glb');
const v=await validator.validateBytes(new Uint8Array(bytes));assert.equal(v.issues.numErrors,0);assert.equal(v.issues.numWarnings,0);
assert.ok(!json.images?.length&&!json.textures?.length&&!json.animations?.length&&!json.cameras?.length&&!json.extensions?.KHR_lights_punctual);assert.ok(json.buffers.every(b=>!b.uri));
const asset=scene.getObjectByName('ASSET_MallShopfrontRollerShutter'),fixed=scene.getObjectByName('FRAME_Fixed'),curtain=scene.getObjectByName('CURTAIN_EditableSlats');
assert.equal(asset.children.length,3);assert.deepEqual(asset.position.toArray(),[0,0,0]);assert.equal(curtain.children.length,30);
let triangles=0,vertices=0,primitives=0;const parts={};scene.traverse(o=>{if(o.isMesh){primitives++;vertices+=o.geometry.attributes.position.count;triangles+=(o.geometry.index?.count??o.geometry.attributes.position.count)/3;const b=new Box3().setFromObject(o);parts[o.name]={min:b.min.toArray(),max:b.max.toArray()};}});
assert.equal(primitives,44);assert.equal(json.materials.length,4);assert.ok(bytes.length<500*1024&&triangles<10000);
const bounds=new Box3().setFromObject(scene),dimensions=bounds.getSize(new Vector3()).toArray();dimensions.forEach((x,i)=>near(x,[3.296,3.338,.69][i]));near(bounds.min.y,0);
const drumBounds=new Box3().setFromObject(scene.getObjectByName('ROLLER_Drum')).getSize(new Vector3()).toArray();drumBounds.forEach((x,i)=>near(x,[3.12,.44,.44][i]));
const clearWidth=parts.TRACK_Right_FrontLip.min[0]-parts.TRACK_Left_FrontLip.max[0];near(clearWidth,2.92);
const fixedTransforms=Object.fromEntries(fixed.children.map(o=>[o.name,o.matrixWorld.toArray()]));
const slats=Array.from({length:28},(_,i)=>scene.getObjectByName('SLAT_'+String(i+1).padStart(2,'0')));
const bottom=scene.getObjectByName('BOTTOM_Rail'),seal=scene.getObjectByName('BOTTOM_Seal');
const originals=Object.fromEntries(curtain.children.map(o=>[o.name,{p:o.position.toArray(),q:o.quaternion.toArray(),s:o.scale.toArray()}]));
const R=.27,K=-.024/(2*Math.PI);const f=r=>.5*(r*Math.sqrt(r*r+K*K)+K*K*Math.asinh(r/Math.abs(K)))/K;const arc=t=>f(R+K*t)-f(R);
function pose(lift){slats.forEach((o,i)=>{const z=.13+i*.1+lift;if(z<=3){o.position.set(0,z,.03);o.rotation.set(0,0,0);}else{let lo=0,hi=16;for(let k=0;k<48;k++){let t=(lo+hi)/2;if(arc(t)<z-3)lo=t;else hi=t;}const t=(lo+hi)/2,r=R+K*t;o.position.set(0,3+r*Math.sin(t),-(.24-r*Math.cos(t)));o.rotation.set(-Math.atan2(r*Math.sin(t)-K*Math.cos(t),r*Math.cos(t)+K*Math.sin(t)),0,0);}});bottom.position.y=.04+lift;seal.position.y=.005+lift;scene.updateMatrixWorld(true);}
function obb(o){o.geometry.computeBoundingBox();return new OBB().fromBox3(o.geometry.boundingBox).applyMatrix4(o.matrixWorld);}
function distanceToSegment(p,a,b){const ab=b.clone().sub(a);const t=Math.max(0,Math.min(1,p.clone().sub(a).dot(ab)/ab.lengthSq()));return p.distanceTo(a.clone().addScaledVector(ab,t));}
export const articulation=[];const centre=new Vector3(0,3,-.24);
for(let step=0;step<=52;step++){
 const lift=step*.05;pose(lift);
 for(const o of fixed.children)assert.deepEqual(o.matrixWorld.toArray(),fixedTransforms[o.name],'Fixed assembly moved');
 for(const moving of curtain.children)for(const stationary of fixed.children)assert.ok(!obb(moving).intersectsOBB(obb(stationary),1e-8),moving.name+' collides with '+stationary.name+' at '+lift);
 for(let i=0;i<28;i++)for(let j=i+1;j<28;j++)assert.ok(!obb(slats[i]).intersectsOBB(obb(slats[j]),1e-8),'Slat collision '+i+'/'+j+' at '+lift);
 for(const s of slats)assert.ok(!obb(s).intersectsOBB(obb(bottom),1e-8),'Bottom rail collides with slat');
 // Conservative full rectangular slat cross-section clears the actual cylindrical drum.
 let minDrumClearance=Infinity;
 for(const s of slats){
  const points=[[-.048,-.006],[.048,-.006],[.048,.006],[-.048,.006]].map(([y,z])=>new Vector3(0,y,z).applyMatrix4(s.matrixWorld));
  const distance=Math.min(...points.map((p,i)=>distanceToSegment(centre,p,points[(i+1)%4])));
  assert.ok(distance>.22,'Slat intersects roller cylinder');minDrumClearance=Math.min(minDrumClearance,distance-.22);
 }
 const clearHeight=new Box3().setFromObject(seal).min.y;near(clearHeight,lift);
 articulation.push({liftMetres:lift,clearHeightMetres:clearHeight,minRollerClearanceMetres:minDrumClearance,fixedUnchanged:true,slatSlatAndFrameCollisions:false,status:'PASS'});
}
pose(0);for(const o of curtain.children){const orig=originals[o.name];o.position.toArray().forEach((v,i)=>near(v,orig.p[i]));o.quaternion.toArray().forEach((v,i)=>near(v,orig.q[i]));assert.deepEqual(o.scale.toArray(),orig.s);}
export const report={id:'mall-shopfront-roller-shutter',glb_bytes:bytes.length,triangles,vertices,primitives,materials:json.materials.length,textures:0,animations:0,dimensions,bounds:{min:bounds.min.toArray(),max:bounds.max.toArray()},parts,clearOpeningMetres:[clearWidth,2.6],poseCases:articulation.length,sha256:createHash('sha256').update(bytes).digest('hex'),validation:{errors:0,warnings:0,validator:v.validatorVersion}};
fs.writeFileSync(root+'reports/assets.json',JSON.stringify(report,null,2)+'\n');fs.writeFileSync(root+'reports/articulation.json',JSON.stringify(articulation,null,2)+'\n');console.log(JSON.stringify(report,null,2));

import fs from 'node:fs';
import assert from 'node:assert/strict';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';
import {Box3,Vector3,Raycaster} from 'three';
import validator from 'gltf-validator';
import {readGlb,near} from './glb.mjs';
const root=fileURLToPath(new URL('.',import.meta.url));
const sha=b=>createHash('sha256').update(b).digest('hex');
const {bytes,json,scene}=await readGlb(root+'exports/optimized.glb');
const result=await validator.validateBytes(new Uint8Array(bytes));
assert.equal(result.issues.numErrors,0);assert.equal(result.issues.numWarnings,0);
assert.ok(!json.animations?.length&&!json.cameras?.length&&!json.extensions?.KHR_lights_punctual);
assert.ok(!json.images?.length&&json.buffers.every(b=>!b.uri));
const asset=scene.getObjectByName('ASSET_MallEscalatorHandrail');assert.ok(asset);
assert.deepEqual(asset.position.toArray(),[0,0,0]);
const radius=.8,theta=Math.PI/6,rise=2.4;
const run=(rise-2*radius*(1-Math.cos(theta)))/Math.tan(theta),end=run/2+radius*Math.sin(theta)+.8;
const bounds=new Box3().setFromObject(scene),dims=bounds.getSize(new Vector3()).toArray();
near(bounds.min.y,0);near(dims[0],2*(end+.428),2e-4);near(dims[1],3.428,2e-4);near(dims[2],.14);
const meshList=[];scene.traverse(o=>{if(o.isMesh)meshList.push(o)});
assert.equal(meshList.length,8);assert.equal(json.materials.length,5);
const expected=['MODULE_ContinuousRubberBelt','MODULE_UpperGuideRail','MODULE_LowerGlazingRail','MODULE_CurvedGlazing','MODULE_Casing_Near','MODULE_Casing_Far','MODULE_ChannelEnd_Lower','MODULE_ChannelEnd_Upper'];
assert.deepEqual(meshList.map(o=>o.name).sort(),expected.sort());
let triangles=0,vertices=0;const parts={};
for(const o of meshList){
 const a=o.geometry.attributes.position,idx=o.geometry.index,points=[],weld=new Map(),remap=[];
 for(let i=0;i<a.count;i++){
  const v=new Vector3().fromBufferAttribute(a,i).applyMatrix4(o.matrixWorld),key=v.toArray().map(x=>x.toFixed(6)).join(',');
  if(!weld.has(key)){weld.set(key,points.length);points.push(v)}remap.push(weld.get(key));
 }
 const edges=new Map(),adj=points.map(()=>new Set());let count=(idx?.count??a.count)/3,volume=0;
 for(let f=0;f<count;f++){
  const tri=[0,1,2].map(j=>remap[idx?idx.getX(3*f+j):3*f+j]);
  assert.equal(new Set(tri).size,3,o.name+' nondegenerate topology');
  const [p,q,r]=tri.map(i=>points[i]);assert.ok(q.clone().sub(p).cross(r.clone().sub(p)).length()>1e-10,o.name+' nonzero triangle');
  volume+=p.dot(q.clone().cross(r))/6;
  for(let j=0;j<3;j++){
   const x=tri[j],y=tri[(j+1)%3],key=x<y?x+','+y:y+','+x;
   const entry=edges.get(key)??{uses:0,direction:0};entry.uses++;entry.direction+=x<y?1:-1;edges.set(key,entry);adj[x].add(y);adj[y].add(x);
  }
 }
 for(const e of edges.values()){assert.equal(e.uses,2,o.name+' closed edge');assert.equal(e.direction,0,o.name+' consistent winding');}
 const unseen=new Set(points.map((_,i)=>i));let components=0;
 while(unseen.size){components++;const q=[unseen.values().next().value];unseen.delete(q[0]);while(q.length){for(const j of adj[q.pop()])if(unseen.delete(j))q.push(j)}}
 assert.equal(components,1);assert.ok(volume>0);
 const euler=points.length-edges.size+count;assert.equal(euler,o.name.includes('ContinuousRubberBelt')?0:2);
 const b=new Box3().setFromObject(o);parts[o.name]={triangles:count,vertices:a.count,weldedVertices:points.length,closedManifold:true,components,euler,positiveVolume_m3:volume,min:b.min.toArray(),max:b.max.toArray()};
 triangles+=count;vertices+=a.count;
}
assert.ok(triangles<8000&&bytes.length<400*1024);
for(const [name,pos] of [['LowerDatum',[-end,0,0]],['UpperDatum',[end,2.4,0]],['LowerBeltTangent',[-end,1,0]],['UpperBeltTangent',[end,3.4,0]],['PairPlane',[0,0,0]]]){
 const anchor=asset.getObjectByName('CONNECTOR_'+name);assert.ok(anchor);anchor.getWorldPosition(new Vector3()).toArray().forEach((x,i)=>near(x,pos[i]));
}
const belt=asset.getObjectByName('MODULE_ContinuousRubberBelt');
const glass=asset.getObjectByName('MODULE_CurvedGlazing');
const upper=asset.getObjectByName('MODULE_UpperGuideRail'),lower=asset.getObjectByName('MODULE_LowerGlazingRail');
const hits=(o,x)=>{
 const raw=new Raycaster(new Vector3(x,5,0),new Vector3(0,-1,0)).intersectObject(o,true).map(h=>h.point.y);
 return raw.filter((v,i)=>i===0||Math.abs(v-raw[i-1])>1e-6);
};
// Double-sided raycasting is a measurement-only setting, not a delivered material change.
for(const o of meshList){o.material=o.material.clone();o.material.side=2;}
const samples=[];
for(const [x,nominal] of [[-2.8,1],[0,2.2],[2.8,3.4]]){
 const b=hits(belt,x),g=hits(glass,x),u=hits(upper,x),l=hits(lower,x);
 assert.equal(b.length,4);assert.equal(g.length,2);assert.equal(u.length,2);assert.equal(l.length,2);
 near((b[0]+b[1])/2,nominal,1e-5);near((b[2]+b[3])/2,nominal-.8,1e-5);
 near(g[0],nominal-.077);near(g[1],nominal-.723);
 const upperGap=b[1]-u[0],lowerGap=l[1]-b[2];
 assert.ok(upperGap>.007&&lowerGap>.024,'belt must not intersect guide supports');
 assert.ok(g[0]>u[1]&&g[0]<u[0]&&g[1]<l[0]&&g[1]>l[1],'glazing edges seat inside supporting rails');
 samples.push({x,upperBeltCentreY:(b[0]+b[1])/2,returnBeltCentreY:(b[2]+b[3])/2,upperGuideGap_m:upperGap,lowerReturnGap_m:lowerGap,glassSeatsInBothRails:true});
}
const bpos=belt.geometry.attributes.position,lowReturn=[],glassReturn=[];
for(const [o,dest] of [[belt,lowReturn],[glass,glassReturn]]){
 const a=o.geometry.attributes.position;
 for(let i=0;i<a.count;i++){
  const p=new Vector3().fromBufferAttribute(a,i).applyMatrix4(o.matrixWorld);
  if(p.x<-end-.1&&Math.abs(p.y-.6)<1e-5)dest.push(p.x);
 }
}
assert.ok(lowReturn.length&&glassReturn.length);
const noseGap=Math.min(...glassReturn)-Math.max(...lowReturn);near(noseGap,.049,2e-4);
const beltBox=new Box3().setFromObject(belt),nearCase=new Box3().setFromObject(asset.getObjectByName('MODULE_Casing_Near'));
near(nearCase.min.z-beltBox.max.z,.01);
near(new Box3().setFromObject(glass).getSize(new Vector3()).z,.012);
const pairA=asset.clone(true),pairB=asset.clone(true);pairA.position.z=.64;pairB.position.z=-.64;pairA.updateMatrixWorld(true);pairB.updateMatrixWorld(true);
const aBox=new Box3().setFromObject(pairA),bBox=new Box3().setFromObject(pairB),pairGap=aBox.min.z-bBox.max.z;
near(pairGap,1.14);assert.equal(aBox.intersectsBox(bBox),false);
export const report={id:'mall-escalator-handrail',glb_bytes:bytes.length,triangles,vertices,primitives:meshList.length,materials:json.materials.length,textures:0,animations:0,dimensions:dims,bounds:{min:bounds.min.toArray(),max:bounds.max.toArray()},parts,sha256:sha(bytes),validation:{errors:0,warnings:0,validator:result.validatorVersion}};
export const geometry={status:'PASS',closedBeltTopology:'One connected, consistently wound genus-one manifold; no open belt ends',nominalSlopeDegrees:30,nominalRise_m:2.4,raySamples:samples,roundedReturnRadialGap_m:noseGap,returnBeltCasingLateralGap_m:.01,pairCasingClearance_m:pairGap,pair:'Two translated instances of one logical asset; no full escalator is implied',future004Integration:'NOT VERIFIED',certification:'None: visual envelope, not manufacturer, passenger-clearance or safety certification'};
// Central slope from actual belt centreline vertices, excluding horizontal/curved ends.
const candidates=[];for(let i=0;i<bpos.count;i++){const p=new Vector3().fromBufferAttribute(bpos,i).applyMatrix4(belt.matrixWorld);if(Math.abs(p.z-.04)<1e-6&&Math.abs(Math.abs(p.x)-run/2)<1e-6&&p.y>1)candidates.push(p)}
const lo=candidates.filter(p=>p.x<0).sort((a,b)=>b.y-a.y)[0],hi=candidates.filter(p=>p.x>0).sort((a,b)=>b.y-a.y)[0];assert.ok(lo&&hi);
geometry.measuredCentralSlopeDegrees=Math.atan2(hi.y-lo.y,hi.x-lo.x)*180/Math.PI;near(geometry.measuredCentralSlopeDegrees,30,1e-5);
fs.writeFileSync(root+'reports/assets.json',JSON.stringify(report,null,2)+'\n');fs.writeFileSync(root+'reports/geometry.json',JSON.stringify(geometry,null,2)+'\n');
console.log(JSON.stringify({metrics:{...report,parts:undefined},geometry},null,2));

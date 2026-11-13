import assert from 'node:assert/strict';import fs from 'node:fs';import {fileURLToPath} from 'node:url';import {createHash} from 'node:crypto';
import {Box3,Vector3,Group} from 'three';import validator from 'gltf-validator';import {readGlb,near} from './glb.mjs';
const root=fileURLToPath(new URL('.',import.meta.url)),layouts=JSON.parse(fs.readFileSync(root+'layouts.json'));
const {bytes,json,scene}=await readGlb(root+'exports/mall-structural-column.glb');
const v=await validator.validateBytes(new Uint8Array(bytes));assert.equal(v.issues.numErrors,0);assert.equal(v.issues.numWarnings,0);
assert.ok(!json.images?.length&&!json.textures?.length&&!json.animations?.length&&!json.cameras?.length&&!json.extensions?.KHR_lights_punctual);
assert.ok(json.buffers.every(b=>!b.uri));const asset=scene.getObjectByName('ASSET_MallStructuralColumn');
assert.deepEqual(asset.position.toArray(),[0,0,0]);near(asset.userData.height_m,3);near(asset.userData.shaft_width_m,.5);
const meshesOf=o=>{const a=[];o.traverse(x=>{if(x.isMesh)a.push(x)});return a;};
let triangles=0,vertices=0,primitives=0;const parts={};
for(const o of meshesOf(scene)){primitives++;vertices+=o.geometry.attributes.position.count;triangles+=(o.geometry.index?.count??o.geometry.attributes.position.count)/3;const b=new Box3().setFromObject(o);parts[o.name]={min:b.min.toArray(),max:b.max.toArray()};}
assert.equal(primitives,13);assert.equal(json.materials.length,3);assert.ok(bytes.length<100*1024&&triangles<2000);
const bounds=new Box3().setFromObject(scene),dimensions=bounds.getSize(new Vector3()).toArray();dimensions.forEach((x,i)=>near(x,[.6,3,.6][i]));near(bounds.min.y,0);
for(const [name,pos] of [['Floor',[0,0,0]],['Ceiling',[0,3,0]]])asset.getObjectByName('CONNECTOR_'+name).getWorldPosition(new Vector3()).toArray().forEach((x,i)=>near(x,pos[i]));
const overlap=(a,b)=>['x','y','z'].map(k=>Math.min(a.max[k],b.max[k])-Math.max(a.min[k],b.min[k]));
const noOverlap=(a,b,label)=>assert.ok(!overlap(a,b).every(x=>x>1e-6),label);
const all=meshesOf(scene);for(let i=0;i<all.length;i++)for(let j=i+1;j<all.length;j++)noOverlap(new Box3().setFromObject(all[i]),new Box3().setFromObject(all[j]),all[i].name+' overlaps '+all[j].name);
const floor=await readGlb(root+'../mall-floor-tile/exports/mall-floor-tile-module.glb'),ceiling=await readGlb(root+'../mall-ceiling-panel/exports/mall-ceiling-panel-module.glb');
export const assemblies=[];
for(const example of layouts.examples){
 const group=new Group(),columns=[],floors=[],ceilings=[];
 const place=(source,positions,target)=>{for(const p of positions){const o=source.clone(true);o.position.fromArray(p);group.add(o);target.push(o)}};
 place(asset,example.columns,columns);place(floor.scene,example.floors,floors);place(ceiling.scene,example.ceilings,ceilings);group.updateMatrixWorld(true);
 const columnMeshes=columns.flatMap(meshesOf),contextMeshes=[...floors,...ceilings].flatMap(meshesOf);
 let comparisons=0;
 for(const a of columnMeshes)for(const b of contextMeshes){comparisons++;noOverlap(new Box3().setFromObject(a),new Box3().setFromObject(b),example.name+': '+a.name+' / '+b.name);}
 for(let i=0;i<columns.length;i++)for(let j=i+1;j<columns.length;j++){const a=new Box3().setFromObject(columns[i]),b=new Box3().setFromObject(columns[j]);near(b.min.x-a.max.x,3);}
 let clearance=Infinity;
 for(const column of columns){
  const b=new Box3().setFromObject(column);near(b.min.y,0);near(b.max.y,3);
  const support=floors.find(f=>Math.abs(f.position.x-column.position.x)<1e-6&&Math.abs(f.position.z-column.position.z)<1e-6);assert.ok(support);near(new Box3().setFromObject(support).max.y,b.min.y);
  assert.ok(!ceilings.some(c=>Math.abs(c.position.x-column.position.x)<1e-6&&Math.abs(c.position.z-column.position.z)<1e-6),'full ceiling bay above column must be omitted');
  for(const c of ceilings){const cb=new Box3().setFromObject(c);near(cb.min.y,3);const dx=Math.max(cb.min.x-b.max.x,b.min.x-cb.max.x,0),dz=Math.max(cb.min.z-b.max.z,b.min.z-cb.max.z,0);clearance=Math.min(clearance,Math.hypot(dx,dz));}
 }
 near(clearance,.3);assert.equal(floors.length,columns.length*9);assert.equal(ceilings.length,columns.length*8);
 assemblies.push({name:example.name,result:'PASS',columns:columns.length,floorModules:floors.length,ceilingModules:ceilings.length,columnContextMeshComparisons:comparisons,penetrations:0,floorContactHeight_m:0,ceilingUndersideHeight_m:3,minimumCapToCeilingClearance_m:clearance,interColumnBaseClearance_m:columns.length>1?3:null,sourceHashes:{floor:createHash('sha256').update(floor.bytes).digest('hex'),ceiling:createHash('sha256').update(ceiling.bytes).digest('hex')}});
}
export const report={id:'mall-structural-column',glb_bytes:bytes.length,triangles,vertices,primitives,materials:json.materials.length,textures:0,animations:0,dimensions,bounds:{min:bounds.min.toArray(),max:bounds.max.toArray()},parts,internalMeshPairChecks:78,sha256:createHash('sha256').update(bytes).digest('hex'),validation:{errors:0,warnings:0,validator:v.validatorVersion}};
fs.writeFileSync(root+'reports/assets.json',JSON.stringify(report,null,2)+'\n');fs.writeFileSync(root+'reports/assemblies.json',JSON.stringify(assemblies,null,2)+'\n');console.log(JSON.stringify({asset:report,assemblies},null,2));

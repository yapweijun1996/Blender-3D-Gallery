// Delivery gate adapted from self-checkout-machine; inspect the actual GLB.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {createHash} from 'node:crypto';
import {Box3, Vector3, Raycaster} from 'three';
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';
import validator from 'gltf-validator';

const output = name => new URL(`reports/${name}`, import.meta.url);
const file = process.argv[2] ?? new URL('exports/optimized.glb', import.meta.url);
const bytes = fs.readFileSync(file);
const json = JSON.parse(bytes.subarray(20, 20+bytes.readUInt32LE(12)));
const validation = await validator.validateBytes(new Uint8Array(bytes), {maxIssues:1000});
if (!process.argv[2]) fs.writeFileSync(output('khronos.json'),JSON.stringify(validation,null,2)+'\n');
assert.equal(validation.issues.numErrors,0);
assert.equal(validation.issues.numWarnings,0);
assert.ok(json.buffers.every(b=>!b.uri));
for (const key of ['images','textures','animations','cameras','skins']) assert.ok(!json[key]?.length,key);
assert.ok(!json.extensions?.KHR_lights_punctual);
assert.equal(json.materials.length,3);
assert.equal(json.materials.filter(m=>m.alphaMode==='BLEND').length,1);
assert.ok(json.materials.every(m=>!m.doubleSided && !m.extensions?.KHR_materials_transmission));

const gltf = await new GLTFLoader().parseAsync(bytes.buffer.slice(bytes.byteOffset,bytes.byteOffset+bytes.byteLength),'');
gltf.scene.updateMatrixWorld(true);
const root = gltf.scene.getObjectByName('ASSET_EscalatorDetail');
assert.ok(root);
assert.equal(gltf.scene.children.length,1);
assert.deepEqual(root.position.toArray(),[0,0,0]);
assert.equal(root.userData.units,'metres');
assert.equal(root.userData.origin,'floor centre');
assert.equal(root.userData.front_axis,'Blender -Y / glTF +Z');
const bounds = new Box3().setFromObject(root,true);
const dimensions = bounds.getSize(new Vector3()).toArray();
assert.ok(Math.abs(bounds.min.y)<1e-7,'floor contact');
assert.ok(Math.abs(bounds.min.x+bounds.max.x)<1e-6,'centred width');
assert.ok(Math.abs(bounds.min.z+bounds.max.z)<1e-6,'centred length');
assert.ok(Math.abs(dimensions[0]-1.67)<1e-6,'overall width including independent sign base');
assert.ok(Math.abs(dimensions[2]-6)<1e-6,'overall run');
const group = root.getObjectByName('STEPS_FutureMotion');
assert.ok(group);
assert.equal(group.children.length,22);
const steps = [...group.children].sort((a,b)=>a.name.localeCompare(b.name));
const stepMeasures=[];
for (let i=0;i<steps.length;i++) {
  const o=steps[i];
  assert.equal(o.name,`STEP_${String(i+1).padStart(3,'0')}`);
  assert.ok(o.isMesh,'one rigid mesh per step');
  assert.equal(o.userData.step_index,i+1);
  const b=new Box3().setFromObject(o,true);
  const d=b.getSize(new Vector3()).toArray();
  assert.ok(Math.abs(d[0]-1)<1e-6,'nominal 1m tread width');
  assert.ok(o.position.z>-2.55 && o.position.z<2.55);
  if (i) {
    assert.ok(o.position.y>=steps[i-1].position.y-1e-6,'nondecreasing treads');
    assert.ok(o.position.y-steps[i-1].position.y<.23,'bounded central riser');
    assert.ok(Math.abs(o.position.z-steps[i-1].position.z+5.1/22)<1e-6,'uniform travel pitch');
  }
  stepMeasures.push({name:o.name,pivot:o.position.toArray(),bounds:{min:b.min.toArray(),max:b.max.toArray()}});
}
assert.ok(steps[0].position.z>0 && steps.at(-1).position.z<0,'front +Z lower entry');
for (const name of ['FRAME_Chassis','HANDRAIL_Belts','BALUSTRADE_Glass','LANDING_Plates','COMB_Plates','SIGNAGE_BlankPost'])
  assert.ok(root.getObjectByName(name),'required feature '+name);

let triangles=0,vertices=0,minimumArea=Infinity;
const parts=[];
root.traverse(o=>{
  if (!o.isMesh) return;
  const {position,normal}=o.geometry.attributes;
  assert.ok(position && normal);
  for (const a of [position,normal]) assert.ok([...a.array].every(Number.isFinite));
  const ids=o.geometry.index, count=ids?.count ?? position.count;
  for(let i=0;i<position.count;i++) assert.ok(Math.abs(new Vector3().fromBufferAttribute(normal,i).length()-1)<1e-5);
  for(let i=0;i<count;i+=3) {
    const [a,b,c]=[0,1,2].map(j=>new Vector3().fromBufferAttribute(position,ids ? ids.getX(i+j) : i+j));
    const area=b.sub(a).cross(c.sub(a)).length()/2;
    assert.ok(area>1e-11,`nondegenerate triangle ${o.name}`);
    minimumArea=Math.min(minimumArea,area);
  }
  triangles+=count/3;
  vertices+=position.count;
  parts.push({name:o.name,material:o.material.name,triangles:count/3});
});
assert.ok(triangles<20000);
assert.ok(bytes.length<1.5*1024*1024);
assert.equal(json.meshes.length,steps.length+6);
assert.equal(parts.length,steps.length+7); // Signpost has steel and graphite primitives.
const landing=root.getObjectByName('LANDING_Plates');
const p=landing.geometry.attributes.position;
const levels=[[],[]];
for(let i=0;i<p.count;i++) {
  const v=new Vector3().fromBufferAttribute(p,i).applyMatrix4(landing.matrixWorld);
  levels[v.z>0 ? 0 : 1].push(v.y);
}
const deckLevels=levels.map(v=>Math.max(...v));
const measuredRise=deckLevels[1]-deckLevels[0];
assert.ok(Math.abs(measuredRise-3.6)<1e-6,'3.6m deck level difference');
// Inspect delivered surfaces, independently of the generator's height schedule.
const surfaceLevels=stepMeasures.map(s=>s.bounds.max[1]);
const rises=surfaceLevels.slice(1).map((y,i)=>y-surfaceLevels[i]);
for (const i of [0,1]) assert.ok(Math.abs(surfaceLevels[i]-deckLevels[0])<1e-6,'flush lower treads');
for (const i of [20,21]) assert.ok(Math.abs(surfaceLevels[i]-deckLevels[1])<1e-6,'flush upper treads');
assert.ok(Math.abs(rises[0])<1e-6 && Math.abs(rises.at(-1))<1e-6,'flat terminals');
for(let i=1;i<4;i++) {
  assert.ok(rises[i]>rises[i-1]+.02,'lower risers open gradually');
  assert.ok(rises.at(-i-1)>rises.at(-i)+.02,'upper risers close gradually');
}
const comb=root.getObjectByName('COMB_Plates');
const combLevels=[[],[]];
for(let i=0;i<comb.geometry.attributes.position.count;i++) {
  const v=new Vector3().fromBufferAttribute(comb.geometry.attributes.position,i).applyMatrix4(comb.matrixWorld);
  combLevels[v.z>0 ? 0 : 1].push(v.y);
}
const combOffsets=combLevels.map((v,i)=>Math.max(...v)-surfaceLevels[i===0 ? 0 : 21]);
assert.ok(combOffsets.every(v=>v>=0 && v<.012),'comb to tread height difference below 12mm');
// Raycast actual casing on both sides across every tread, including its edges.
const frame=root.getObjectByName('FRAME_Chassis');
const casingBounds=new Box3().setFromObject(frame,true);
assert.ok(Math.abs(casingBounds.getSize(new Vector3()).x-1.32)<1e-6,'outside casing width');
const centreX=steps[0].position.x;
const signBounds=new Box3().setFromObject(root.getObjectByName('SIGNAGE_BlankPost'),true);
const signClearance={};
for(const [label,name] of [['casing','FRAME_Chassis'],['handrail','HANDRAIL_Belts'],['glass','BALUSTRADE_Glass']]) {
  const other=new Box3().setFromObject(root.getObjectByName(name),true);
  signClearance[label+'_lateral_gap_m']=signBounds.min.x-other.max.x;
  assert.ok(signClearance[label+'_lateral_gap_m']>.12,'whole sign separated from '+label);
}
assert.ok(Math.abs(signBounds.min.y)<1e-7,'sign base rests on the floor');
const ray=new Raycaster();
let treadLevelSamples=0,maximumTreadLevelSpread=0;
for(let i=0;i<steps.length;i++) {
  const step=steps[i];
  const pitch=stepMeasures[i].bounds.max[2]-stepMeasures[i].bounds.min[2];
  const heights=[];
  for(const offset of [-.35,0,.35]) {
    ray.set(new Vector3(step.position.x,10,step.position.z+offset*pitch),new Vector3(0,-1,0));
    const hit=ray.intersectObject(step,false)[0];
    assert.ok(hit && Math.abs(hit.point.y-surfaceLevels[i])<.0006,'sample reaches a tread rib below the nosing');
    heights.push(hit.point.y);
    treadLevelSamples++;
  }
  const spread=Math.max(...heights)-Math.min(...heights);
  assert.ok(spread<1e-6,'horizontal tread surface '+step.name);
  maximumTreadLevelSpread=Math.max(maximumTreadLevelSpread,spread);
}
let minimumTopCover=Infinity,minimumBottomCover=Infinity,skirtSamples=0;
for(const step of stepMeasures) {
  for(const side of [-1,1]) for(let j=0;j<=8;j++) {
    const z=step.bounds.min[2]+(step.bounds.max[2]-step.bounds.min[2])*j/8;
    ray.set(new Vector3(centreX+side*.505,10,z),new Vector3(0,-1,0));
    const top=ray.intersectObject(frame,false)[0];
    assert.ok(top,'casing above tread side');
    const topCover=top.point.y-step.bounds.max[1];
    assert.ok(topCover>.015,'skirt hides nosings and gaps');
    ray.set(new Vector3(centreX+side*.505,-1,z),new Vector3(0,1,0));
    const bottom=ray.intersectObject(frame,false)[0];
    assert.ok(bottom,'casing below tread side');
    const bottomCover=step.bounds.min[1]-bottom.point.y;
    assert.ok(bottomCover>0,'step does not protrude below casing');
    minimumTopCover=Math.min(minimumTopCover,topCover);
    minimumBottomCover=Math.min(minimumBottomCover,bottomCover);
    skirtSamples++;
  }
}
const maxRise=Math.max(...rises),pitch=steps[0].position.z-steps[1].position.z;
const report={result:'PASS',id:'escalator-detail',glb_bytes:bytes.length,triangles,vertices,
  stored_meshes:json.meshes.length,mesh_primitives:parts.length,materials:json.materials.length,
  transparent_primitives:parts.filter(p=>p.material==='Blue green balustrade glass').length,
  images:0,animations:0,independent_step_nodes:steps.length,dimensions,
  bounds:{min:bounds.min.toArray(),max:bounds.max.toArray()},
  tread_width_m:new Box3().setFromObject(steps[0],true).getSize(new Vector3()).x,
  walking_surface_levels_m:deckLevels,deck_rise_m:measuredRise,
  step_pitch_m:pitch,step_surface_levels_m:surfaceLevels,step_rises_m:rises,
  maximum_step_rise_m:maxRise,maximum_incline_degrees:Math.atan2(maxRise,pitch)*180/Math.PI,
  transition:{flat_treads_per_terminal:2,comb_above_tread_m:combOffsets,
    skirt_sample_count:skirtSamples,minimum_skirt_top_cover_m:minimumTopCover,
    minimum_skirt_bottom_cover_m:minimumBottomCover},
  signage:{bounds:{min:signBounds.min.toArray(),max:signBounds.max.toArray()},...signClearance},
  tread_centre_x_m:centreX,horizontal_tread_sample_count:treadLevelSamples,maximum_tread_level_spread_m:maximumTreadLevelSpread,
  minimum_triangle_area_m2:minimumArea,steps:stepMeasures,
  sha256:createHash('sha256').update(bytes).digest('hex'),
  validation:{errors:validation.issues.numErrors,warnings:validation.issues.numWarnings,version:validator.version()},
  budget:{triangles_exclusive:20000,bytes_exclusive:1572864,materials_max:3},parts};
if(!process.argv[2]) fs.writeFileSync(output('assets.json'),JSON.stringify(report,null,2)+'\n');
console.log(JSON.stringify(report,null,2));

// Delivery gate adapted from self-checkout-machine; inspect the actual GLB.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {createHash} from 'node:crypto';
import {Box3, Vector3} from 'three';
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
assert.ok(Math.abs(dimensions[0]-1.32)<1e-6,'outside casing width');
assert.ok(Math.abs(dimensions[2]-6)<1e-6,'overall run');
const group = root.getObjectByName('STEPS_FutureMotion');
assert.ok(group);
assert.equal(group.children.length,18);
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
  assert.ok(o.position.z>-.001-2.41 && o.position.z<2.41+.001);
  if (i) {
    assert.ok(Math.abs(o.position.y-steps[i-1].position.y-.2)<1e-6,'uniform rise');
    assert.ok(Math.abs(o.position.z-steps[i-1].position.z+5.1/18)<1e-6,'uniform travel pitch');
    assert.ok(b.min.z>new Box3().setFromObject(steps[i-1],true).min.z-5.1/18-1e-6);
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
assert.equal(json.meshes.length,24);
assert.equal(parts.length,25); // Signpost has steel and graphite primitives.
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
const report={result:'PASS',id:'escalator-detail',glb_bytes:bytes.length,triangles,vertices,
  stored_meshes:json.meshes.length,mesh_primitives:parts.length,materials:json.materials.length,
  transparent_primitives:parts.filter(p=>p.material==='Blue green balustrade glass').length,
  images:0,animations:0,independent_step_nodes:steps.length,dimensions,
  bounds:{min:bounds.min.toArray(),max:bounds.max.toArray()},
  tread_width_m:new Box3().setFromObject(steps[0],true).getSize(new Vector3()).x,
  walking_surface_levels_m:deckLevels,deck_rise_m:measuredRise,
  step_pitch_m:steps[0].position.z-steps[1].position.z,
  step_rise_m:steps[1].position.y-steps[0].position.y,
  incline_degrees:Math.atan2(steps[1].position.y-steps[0].position.y,steps[0].position.z-steps[1].position.z)*180/Math.PI,
  minimum_triangle_area_m2:minimumArea,steps:stepMeasures,
  sha256:createHash('sha256').update(bytes).digest('hex'),
  validation:{errors:validation.issues.numErrors,warnings:validation.issues.numWarnings,version:validator.version()},
  budget:{triangles_exclusive:20000,bytes_exclusive:1572864,materials_max:3},parts};
if(!process.argv[2]) fs.writeFileSync(output('assets.json'),JSON.stringify(report,null,2)+'\n');
console.log(JSON.stringify(report,null,2));

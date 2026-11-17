// Independent actual-GLB gate, following the self-checkout-machine workflow.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {createHash} from 'node:crypto';
import {Box3, Vector3} from 'three';
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';
import validator from 'gltf-validator';

const file = process.argv[2] ?? new URL('exports/optimized.glb',import.meta.url);
const bytes = fs.readFileSync(file);
const json = JSON.parse(bytes.subarray(20,20+bytes.readUInt32LE(12)));
const validation = await validator.validateBytes(new Uint8Array(bytes),{maxIssues:1000});
const write = (name,data) => fs.writeFileSync(new URL('reports/'+name,import.meta.url),JSON.stringify(data,null,2)+'\n');
if (!process.argv[2]) write('khronos.json',validation);
assert.equal(validation.issues.numErrors,0);
assert.equal(validation.issues.numWarnings,0);
assert.ok(json.buffers.every(b=>!b.uri));
for (const key of ['images','textures','animations','skins','cameras']) assert.ok(!json[key]?.length,key);
assert.ok(!json.extensions?.KHR_lights_punctual);
assert.equal(json.materials.length,3);
assert.ok(json.materials.every(m=>!m.doubleSided && (!m.alphaMode || m.alphaMode==='OPAQUE')));
const reflective = json.materials.find(m=>m.name==='Polished stainless and mirror');
assert.equal(reflective.pbrMetallicRoughness.metallicFactor ?? 1,1);
assert.ok(reflective.pbrMetallicRoughness.roughnessFactor>=.18 && reflective.pbrMetallicRoughness.roughnessFactor<=.25);
const luminous = json.materials.find(m=>m.name==='Warm white ceiling diffuser');
assert.ok(luminous.emissiveFactor.every(x=>x>0));

const gltf = await new GLTFLoader().parseAsync(bytes.buffer.slice(bytes.byteOffset,bytes.byteOffset+bytes.byteLength),'');
gltf.scene.updateMatrixWorld(true);
const root = gltf.scene.getObjectByName('ASSET_ElevatorInterior');
assert.ok(root);
assert.equal(gltf.scene.children.length,1);
assert.deepEqual(root.position.toArray(),[0,0,0]);
assert.equal(root.userData.units,'metres');
assert.equal(root.userData.origin,'floor centre');
assert.equal(root.userData.finished_floor_y_m,0);
assert.equal(root.userData.front_axis,'Blender -Y / glTF +Z');
const bounds = new Box3().setFromObject(root,true);
const dimensions = bounds.getSize(new Vector3()).toArray();
for (const [i,expected] of [1.6,2.4,1.5].entries()) assert.ok(Math.abs(dimensions[i]-expected)<1e-6);
assert.ok(Math.abs(bounds.min.y+.06)<1e-7,'base extends below the finished-floor datum');
assert.ok(Math.abs(bounds.max.y-2.34)<1e-6);
for (const axis of ['x','z']) assert.ok(Math.abs(bounds.min[axis]+bounds.max[axis])<1e-6);

const names = ['CABIN_Panels','CONTROL_UnlabelledButtons','FLOOR_Stone','FRAME_TrimAndHandrail',
  'MIRROR_Rear','LIGHT_Ceiling','DOOR_LeftInner','DOOR_LeftOuter','DOOR_RightInner','DOOR_RightOuter'];
for (const name of names) assert.ok(root.getObjectByName(name)?.isMesh,'required feature '+name);
const b = name => new Box3().setFromObject(root.getObjectByName(name),true);
assert.ok(Math.abs(b('FLOOR_Stone').max.y)<1e-7,'floor finish and recessed tracks meet Y=0');
const doors = names.filter(n=>n.startsWith('DOOR_'));
const doorBounds = doors.map(name=>({name,min:b(name).min.toArray(),max:b(name).max.toArray()}));
for (const door of doorBounds) {
  assert.ok(Math.abs(door.min[1]-.006)<1e-6 && Math.abs(door.max[1]-2.154)<1e-6,'door sill/head clearance');
  assert.ok(door.min[2]>.65,'front +Z open leaves');
  assert.ok(door.min[0]>=-.8 && door.max[0]<=.8,'stowed inside car');
  if (door.name.includes('Left')) assert.ok(door.max[0]<-.45,'left leaf clears aperture');
  else assert.ok(door.min[0]>.45,'right leaf clears aperture');
}
assert.ok(b('MIRROR_Rear').max.z<-.65,'rear mirror');
assert.ok(b('MIRROR_Rear').min.y>1.19,'mirror above handrail');
assert.ok(b('CONTROL_UnlabelledButtons').min.x>.68,'inner right-wall controls');
assert.ok(b('LIGHT_Ceiling').min.y>2.26,'ceiling light');

let triangles=0,vertices=0,minimumArea=Infinity;
const parts=[];
root.traverse(o=>{
  if (!o.isMesh) return;
  const {position,normal,color} = o.geometry.attributes;
  assert.ok(position && normal);
  for (const attribute of [position,normal,color].filter(Boolean)) assert.ok([...attribute.array].every(Number.isFinite));
  if (o.material.name==='Neutral panels and stone') assert.ok(color,'neutral material needs vertex colours');
  for (let i=0;i<normal.count;i++) assert.ok(Math.abs(new Vector3().fromBufferAttribute(normal,i).length()-1)<1e-5);
  const ids=o.geometry.index,count=ids?.count ?? position.count;
  for (let i=0;i<count;i+=3) {
    const [a,b,c]=[0,1,2].map(j=>new Vector3().fromBufferAttribute(position,ids ? ids.getX(i+j) : i+j));
    const area=b.sub(a).cross(c.sub(a)).length()/2;
    assert.ok(area>1e-11,'nondegenerate triangle '+o.name);
    minimumArea=Math.min(minimumArea,area);
  }
  triangles+=count/3;
  vertices+=position.count;
  parts.push({name:o.name,material:o.material.name,triangles:count/3});
});
assert.ok(triangles<15000);
assert.ok(bytes.length<1572864);
assert.equal(json.meshes.length,10);
assert.equal(parts.length,10);
const report={result:'PASS',id:'elevator-interior',glb_bytes:bytes.length,triangles,vertices,
  stored_meshes:json.meshes.length,mesh_primitives:parts.length,materials:json.materials.length,
  images:json.images?.length ?? 0,animations:gltf.animations.length,dimensions,
  bounds:{min:bounds.min.toArray(),max:bounds.max.toArray()},door_leaves:doorBounds,
  finished_floor_y_m:b('FLOOR_Stone').max.y,
  minimum_triangle_area_m2:minimumArea,parts,sha256:createHash('sha256').update(bytes).digest('hex'),
  validation:{errors:validation.issues.numErrors,warnings:validation.issues.numWarnings,version:validator.version()},
  budget:{triangles_exclusive:15000,bytes_exclusive:1572864,materials_max:3}};
if (!process.argv[2]) write('assets.json',report);
console.log(JSON.stringify(report,null,2));

import assert from 'node:assert/strict';import fs from 'node:fs';import {fileURLToPath} from 'node:url';import {createHash} from 'node:crypto';import {Box3,Vector3} from 'three';import validator from 'gltf-validator';import {readGlb} from './glb.mjs';
const dir=fileURLToPath(new URL('.',import.meta.url)),spec=JSON.parse(fs.readFileSync(dir+'backlog.json'));
const {bytes,json,scene}=await readGlb(dir+'exports/optimized.glb');const v=await validator.validateBytes(new Uint8Array(bytes));assert.equal(v.issues.numErrors,0);assert.equal(v.issues.numWarnings,0);
const root=scene.getObjectByName(spec.root);assert.ok(root);assert.deepEqual(root.position.toArray(),[0,0,0]);assert.equal(root.userData.units,'metres');assert.ok(json.buffers.every(x=>!x.uri));assert.ok(!json.textures?.length&&!json.images?.length&&!json.animations?.length&&!json.cameras?.length&&!json.extensions?.KHR_lights_punctual);
let triangles=0,vertices=0;const parts={};scene.traverse(o=>{if(o.isMesh){const g=o.geometry;assert.ok(g.attributes.normal);const p=g.attributes.position;vertices+=p.count;triangles+=(g.index?.count??p.count)/3;for(const x of p.array)assert.ok(Number.isFinite(x));const b=new Box3().setFromObject(o);parts[o.name]={min:b.min.toArray(),max:b.max.toArray()};}});
assert.ok(bytes.length<spec.budget_bytes);assert.ok(triangles<spec.budget_triangles);assert.ok(Object.keys(parts).length>=5);const bounds=new Box3().setFromObject(scene),dimensions=bounds.getSize(new Vector3()).toArray();assert.ok(Math.abs(bounds.min.y)<.001);const expected=spec.expected_x_y;assert.ok(Math.abs(dimensions[0]-expected[0])<.015);assert.ok(Math.abs(dimensions[1]-expected[1])<.015);
const count=p=>Object.keys(parts).filter(n=>n.startsWith(p)).length;
if(spec.id===380){assert.equal(count('WHEEL_Rubber'),4);assert.equal(count('BIN_Ingredient'),3);assert.equal(count('DESSERT_PandanNoodle'),10);assert.ok(scene.getObjectByName('EDITABLE_Lettering_Export'));}
if(spec.id===381||spec.id===382){assert.equal(count('VEHICLE_Lens'),3);assert.equal(count('VEHICLE_VisorTop'),3);assert.equal(count('VEHICLE_VisorSide'),6);}
if(spec.id===381){assert.equal(count('BUTTON_Pedestrian'),1);}
if(spec.id===382){assert.equal(count('POLE_YellowBand'),3);}
if(spec.id===383){assert.equal(count('COLUMN_Gantry'),2);assert.equal(count('SENSOR_Housing'),3);assert.ok(scene.getObjectByName('EDITABLE_Lettering_Export'));}
if(spec.id===384){assert.equal(count('COLUMN_Canopy'),6);assert.equal(count('LANE_Display'),2);assert.equal(count('BASE_Island'),3);}
// Front-facing elements must remain on glTF +Z after the Blender -Y export mapping.
if(spec.id===380||spec.id===383){assert.ok(parts.EDITABLE_Lettering_Export.min[2]>0);}
if(spec.id===381||spec.id===382){for(const [name,b] of Object.entries(parts))if(name.startsWith('VEHICLE_Lens'))assert.ok(b.min[2]>.20);}
const report={id:spec.title,backlog_id:spec.id,sha256:createHash('sha256').update(bytes).digest('hex'),glb_bytes:bytes.length,triangles,vertices,primitives:Object.keys(parts).length,materials:json.materials.length,textures:0,animations:0,dimensions,bounds:{min:bounds.min.toArray(),max:bounds.max.toArray()},parts,validation:{errors:0,warnings:0,validator:v.validatorVersion},result:'PASS'};fs.writeFileSync(dir+'reports/assets.json',JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report,null,2));

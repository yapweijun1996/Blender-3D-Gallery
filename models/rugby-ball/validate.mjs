import assert from 'node:assert/strict';
import fs from 'node:fs';
import { createHash } from 'node:crypto';
import { fileURLToPath } from 'node:url';
import { Box3, Vector3, Raycaster } from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import validator from 'gltf-validator';

const dir = fileURLToPath(new URL('.', import.meta.url));
const spec = JSON.parse(fs.readFileSync(dir + 'backlog.json'));
const source = JSON.parse(fs.readFileSync(dir + 'reports/source-geometry.json'));
const bytes = fs.readFileSync(dir + 'exports/optimized.glb');
const json = JSON.parse(bytes.subarray(20, 20 + bytes.readUInt32LE(12)));
const validation = await validator.validateBytes(new Uint8Array(bytes), { maxIssues: 100 });
fs.writeFileSync(dir + 'reports/khronos.json', JSON.stringify(validation, null, 2) + '\n');
assert.equal(validation.issues.numErrors, 0);
assert.equal(validation.issues.numWarnings, 0);
// Node has no image decoder: parse geometry from a copy without the texture binding.
const jsonLength = bytes.readUInt32LE(12);
const bin = bytes.subarray(28 + jsonLength, 28 + jsonLength + bytes.readUInt32LE(20 + jsonLength));
const geometryJson = structuredClone(json);
delete geometryJson.images;
delete geometryJson.textures;
delete geometryJson.samplers;
for (const material of geometryJson.materials) delete material.normalTexture;
const jsonChunk = Buffer.from(JSON.stringify(geometryJson));
const paddedJson = Buffer.alloc(Math.ceil(jsonChunk.length / 4) * 4, 0x20);
jsonChunk.copy(paddedJson);
const binHeader = Buffer.alloc(8);
binHeader.writeUInt32LE(bin.length, 0);
binHeader.writeUInt32LE(0x004e4942, 4);
const header = Buffer.alloc(20);
header.writeUInt32LE(0x46546c67, 0);
header.writeUInt32LE(2, 4);
header.writeUInt32LE(20 + paddedJson.length + 8 + bin.length, 8);
header.writeUInt32LE(paddedJson.length, 12);
header.writeUInt32LE(0x4e4f534a, 16);
const geometryGlb = Buffer.concat([header, paddedJson, binHeader, bin]);
const gltf = await new GLTFLoader().parseAsync(geometryGlb.buffer.slice(geometryGlb.byteOffset, geometryGlb.byteOffset + geometryGlb.byteLength), '');
gltf.scene.updateMatrixWorld(true);
const root = gltf.scene.getObjectByName(spec.root);
assert.ok(root);
assert.deepEqual(root.position.toArray(), [0, 0, 0]);
assert.equal(root.userData.units, 'metres');
assert.equal(root.userData.front_axis, 'Blender -Y / glTF +Z');
assert.equal(gltf.animations.length, 0);

assert.equal(root.userData.up_axis,'Blender +Z / glTF +Y');
assert.ok((json.images??[]).every(i=>i.bufferView!==undefined && i.uri===undefined && i.mimeType==='image/jpeg'));
assert.ok(json.buffers.every(b=>b.uri===undefined));
assert.ok(!json.cameras?.length && !json.extensions?.KHR_lights_punctual);
assert.equal(json.meshes.length,1,'one combined export mesh');
for(const m of json.materials) assert.equal(m.pbrMetallicRoughness.metallicFactor,0);
const byMaterial=new Map();
let triangles=0,vertices=0,primitives=0;
gltf.scene.traverse(o=>{
 if(!o.isMesh)return;
 const g=o.geometry,pos=g.attributes.position;
 for(const a of Object.values(g.attributes))assert.ok(Array.from(a.array).every(Number.isFinite),'finite attributes');
 assert.ok(g.attributes.normal);
 const list=Array.from({length:pos.count},(_,i)=>new Vector3().fromBufferAttribute(pos,i).applyMatrix4(o.matrixWorld));
 const count=g.index?.count??pos.count,tris=[];
 for(let i=0;i<count;i+=3){
  const t=[0,1,2].map(k=>g.index?g.index.getX(i+k):i+k);
  const a=list[t[1]].clone().sub(list[t[0]]),b=list[t[2]].clone().sub(list[t[0]]);
  assert.ok(a.cross(b).lengthSq()>1e-28,'nondegenerate triangles');tris.push(t);
 }
 const group=byMaterial.get(o.material.name)??{list:[],tris:[]};const off=group.list.length;
 group.list.push(...list);group.tris.push(...tris.map(t=>t.map(i=>i+off)));byMaterial.set(o.material.name,group);
 triangles+=count/3;vertices+=pos.count;primitives++;
});
assert.ok(triangles<=spec.budget.triangles);assert.ok(bytes.length<=spec.budget.bytes);
assert.ok(primitives<=spec.budget.mesh_primitives);assert.ok(json.materials.length<=spec.budget.materials);
assert.equal(json.textures?.length??0,spec.budget.textures);
const bounds=new Box3().setFromObject(gltf.scene,true),dimensions=bounds.getSize(new Vector3()).toArray();
assert.ok(bounds.min.y>=-1e-6&&bounds.min.y<.00025,'floor contact');
assert.ok(Math.abs(bounds.min.x+bounds.max.x)<.0004&&Math.abs(bounds.min.z+bounds.max.z)<.0004,'centred X/Z');
function groups(data){
 const ids=data.list.map(p=>p.toArray().map(v=>Math.round(v*1e7)).join(','));
 const parent=new Map(ids.map(k=>[k,k]));
 const find=k=>{while(parent.get(k)!==k){parent.set(k,parent.get(parent.get(k)));k=parent.get(k)}return k};
 for(const t of data.tris){parent.set(find(ids[t[1]]),find(ids[t[0]]));parent.set(find(ids[t[2]]),find(ids[t[0]]))}
 const out=new Map();ids.forEach((id,i)=>{const k=find(id);if(!out.has(k))out.set(k,[]);out.get(k).push(data.list[i])});return [...out.values()];
}
function combine(names){const d={list:[],tris:[]};for(const n of names){const v=byMaterial.get(n);assert.ok(v,n);const k=d.list.length;d.list.push(...v.list);d.tris.push(...v.tris.map(t=>t.map(i=>i+k)))}return d}
const features={};
if(spec.slug==='american-football'||spec.slug==='rugby-ball'){
 const rugby=spec.slug==='rugby-ball',a=source.length_m/2,b=source.short_circumference_m/(2*Math.PI);
 assert.ok(Math.abs(dimensions[0]-2*a)<.0001,'midpoint length');
 assert.ok(Math.abs(dimensions[2]-2*b)<.0001,'midpoint short circumference');
 assert.ok(Math.abs(dimensions[1]-2*b)<(rugby?.0002:.0045),'height, including raised laces');
 const skin=combine(rugby?['Grip white rubber','Generic teal bands']:['Pebbled brown leather']);
 assert.equal(groups(skin).length,4,'exactly four separated panel surfaces');features.panels=4;
 const seam=byMaterial.get('Recessed seam bed');assert.ok(seam);
 for(const ang of [0,Math.PI/2,Math.PI,Math.PI*1.5]){
  const target=new Vector3(0,b+(b-.0013)*Math.cos(ang),-(b-.0013)*Math.sin(ang));
  assert.ok(seam.list.some(v=>v.distanceTo(target)<.0002),'recessed seam at centre');
  assert.ok(!skin.list.some(v=>v.distanceTo(new Vector3(0,b+b*Math.cos(ang),-b*Math.sin(ang)))<.0005),'skin leaves groove');
 }
 let length=0,last=null;
 for(let i=0;i<=4000;i++){const t=Math.PI*i/4000,p=[a*Math.cos(t),b*Math.sin(t)**source.profile_exponent];if(last)length+=2*Math.hypot(p[0]-last[0],p[1]-last[1]);last=p}
 assert.ok(Math.abs(length-source.long_circumference_m)<.00002,'midpoint long circumference from profile');
 features.long_circumference_m=length;features.short_circumference_m=2*Math.PI*b;
 if(!rugby){
  const lace=groups(byMaterial.get('Ivory lace'));
  assert.equal(lace.length,10,'white strip, one long lace and eight crossings');
  const crosses=lace.filter(v=>{const s=new Box3().setFromPoints(v).getSize(new Vector3());return s.z>.02&&s.x<.004});
  assert.equal(crosses.length,8,'eight crossing laces as geometry');features.crossing_laces=8;features.long_laces=1;
 }else assert.ok(byMaterial.get('Generic teal bands').tris.length>100,'generic colour bands exist');
 for(const m of json.materials.filter(m=>/leather|rubber|bands/.test(m.name)&&m.name!=='Recessed seam bed'))assert.ok(m.normalTexture,'embedded baked grip');
}else if(spec.slug==='badminton-shuttlecock'){
 const vanes=groups(byMaterial.get('Ivory feather vanes'));
 const large=vanes.filter(v=>new Box3().setFromPoints(v).getSize(new Vector3()).y>.035);
 assert.equal(large.length,16,'sixteen thin solid feather vanes');
 assert.equal(groups(byMaterial.get('Feather shafts')).length,16,'sixteen geometric shafts');
 assert.equal(groups(byMaterial.get('Cream binding thread')).length,2,'two binding bands');
 assert.ok(Math.abs(dimensions[1]-source.height_m)<.0005,'BWF feather length is measured above cork');
 assert.ok(Math.abs(dimensions[0]-.063)<.001&&Math.abs(dimensions[2]-.063)<.001,'63 mm feather tip circle');
 const cork=byMaterial.get('White cork cover'),cs=new Box3().setFromPoints(cork.list).getSize(new Vector3());
 assert.ok(Math.abs(cs.x-.0265)<.0001&&Math.abs(cs.z-.0265)<.0001,'26.5 mm cork');
 const c=new Vector3(0,.01325,0);
 assert.ok(cork.list.filter(p=>p.y<.0132).every(p=>Math.abs(p.distanceTo(c)-.01325)<.00001),'hemispherical cork bottom');
 Object.assign(features,{feathers:16,thread_bands:2,feather_length_m:.066,tip_circle_diameter_m:.063,base_diameter_m:.0265});
}else{
 const strips=groups(byMaterial.get('Golden synthetic woven strips'));
 assert.equal(strips.length,6,'six separate closed woven strips');
 const normals=source.strip_normals.map(p=>new Vector3(p[0],p[2],-p[1]));
 const centre=new Vector3(...source.sphere_centre_glb),R=source.nominal_radius_m;
 const ray=new Raycaster();
 const hit=direction=>{ray.set(centre.clone().addScaledVector(direction,R*2),direction.clone().negate());return ray.intersectObject(gltf.scene,true)};
 for(const n of normals)for(const sign of [-1,1])assert.equal(hit(n.clone().multiplyScalar(sign)).length,0,'see through every pentagonal opening');
 const ico=normals.flatMap(n=>[n,n.clone().negate()]),junctions=[];
 for(let i=0;i<12;i++)for(let j=i+1;j<12;j++)for(let k=j+1;k<12;k++){
  if([ico[i].dot(ico[j]),ico[j].dot(ico[k]),ico[k].dot(ico[i])].every(v=>Math.abs(v-1/Math.sqrt(5))<1e-5))junctions.push(ico[i].clone().add(ico[j]).add(ico[k]).normalize());
 }
 assert.equal(junctions.length,20,'twenty triangular junction directions');
 for(const n of junctions)assert.ok(hit(n).length>0,'triangular regions are woven material');
 // Six great-circle ribbons leave twelve convex pentagonal regions. Each has five active walls.
 for(const hole of ico)assert.equal(normals.filter(n=>Math.abs(n.dot(hole))<.5).length,5,'five walls around each hole');
 assert.ok(dimensions.every(d=>Math.abs(d-.43/Math.PI)<.001),'43 cm spherical envelope');
 for(const strip of strips){const radii=strip.map(p=>p.distanceTo(centre));assert.ok(Math.max(...radii)-Math.min(...radii)>.002,'over/under relief')}
 Object.assign(features,{strips:6,pentagonal_openings:12,triangular_junctions:20,see_through:true,circumference_m:.43});
}
const report={result:'PASS',id:spec.slug,glb_bytes:bytes.length,triangles,vertices,meshes:json.meshes.length,primitives,
 materials:json.materials.length,textures:json.textures?.length??0,animations:gltf.animations.length,
 dimensions_m:dimensions,bounds_m:{min:bounds.min.toArray(),max:bounds.max.toArray()},...features,
 sha256:createHash('sha256').update(bytes).digest('hex'),budget:spec.budget,
 validation:{errors:validation.issues.numErrors,warnings:validation.issues.numWarnings,infos:validation.issues.numInfos}};
fs.writeFileSync(dir+'reports/assets.json',JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report,null,2));

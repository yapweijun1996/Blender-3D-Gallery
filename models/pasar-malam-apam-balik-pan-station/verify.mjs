import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {readFile} from 'node:fs/promises';
import {validateBytes} from 'gltf-validator';
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';
import {Box3,Raycaster,Vector3} from 'three';
const id='pasar-malam-apam-balik-pan-station';
const data=await readFile(process.argv[2]??new URL('./exports/'+id+'.glb',import.meta.url));
const json=JSON.parse(data.subarray(20,20+data.readUInt32LE(12)));
const k=await validateBytes(new Uint8Array(data),{uri:id+'.glb'});
assert.equal(k.issues.numErrors,0,JSON.stringify(k.issues));assert.equal(k.issues.numWarnings,0,JSON.stringify(k.issues));
assert.equal(k.issues.numInfos,0,JSON.stringify(k.issues));assert.equal(k.issues.numHints,0,JSON.stringify(k.issues));
assert.deepEqual(json.buffers.map(b=>b.uri),[undefined]);assert.equal(json.images?.length??0,0);
assert.equal(json.animations?.length??0,0);assert.equal(json.cameras?.length??0,0);
const g=await new GLTFLoader().parseAsync(data.buffer.slice(data.byteOffset,data.byteOffset+data.byteLength),'');
assert.equal(g.animations.length,0);
const s=g.scene;s.updateMatrixWorld(true);
const names=['APAM_OPEN_PAN_LEFT','APAM_OPEN_PAN_RIGHT','REMOVABLE_DOMED_LID','OPEN_WIRE_COOLING_RACK','ONE_FIXED_ORIGINAL_FOLDED_APAM_SAMPLE'];
for(const name of names)assert.ok(s.getObjectByName(name),name);
const meshes=(p)=>{const m=[];s.traverse(n=>{if(n.name.startsWith(p)&&n.isMesh)m.push(n)});return m};
const parts=(p)=>s.getObjectByName(p);
const gdown=new Vector3(0,-1,0);
const hit=(o,x,z,up=false)=>{
 const r=new Raycaster(new Vector3(x,up?.56:.84,z),up?new Vector3(0,1,0):gdown);
 return r.intersectObjects(o,true)[0]?.point;
};
let panDepths=[],rays=0;
for(const [where,x] of [['LEFT',-.448],['RIGHT',-.025]]){
 const pan=meshes('Walled_concave_radial_pan_basin_'+where);
 assert.equal(pan.length,where==='LEFT'?3:4);
 let minRim=1,maxFloor=0,fit=0;
 const rest=meshes('Short_passive_annular_iron_trivet_'+where);
 assert.ok(rest.length>=2);
 for(let i=0;i<24;i++){
  const a=i*Math.PI/12;const r=.152;
  const rim=hit(pan,x+r*Math.cos(a),.078+r*Math.sin(a));
  const flo=hit(pan,x+.104*Math.cos(a),.078+.104*Math.sin(a));
  assert.ok(rim&&flo);
  rays+=2;minRim=Math.min(minRim,rim.y);maxFloor=Math.max(maxFloor,flo.y);
  const sup=hit(rest,x+.121*Math.cos(a),.078+.121*Math.sin(a));
  const under=hit(pan,x+.121*Math.cos(a),.078+.121*Math.sin(a),true);
  assert.ok(sup&&under);rays+=2;fit=Math.max(fit,Math.abs(sup.y-under.y));
 }
 const depth=minRim-maxFloor;assert.ok(depth>.04);assert.ok(fit<.0001,[where,fit]);
 panDepths.push({where,cavityDepth:depth,panToTrivetGap:fit});
}
const wires=meshes('Independent_cooling_rack_wire');
assert.equal(wires.length,16);
let apertures=0;
for(const x of [.291,.365,.445,.536])for(let j=0;j<15;j++){
 const y0=.055+.175-.023*j;
 assert.ok(hit(wires,x,y0));
 assert.equal(hit(wires,x,y0-.0115),undefined);
 apertures++;
}
const bounds=new Box3().setFromObject(s,true);
assert.ok(Math.abs(bounds.min.y)<.005);
assert.ok(bounds.max.y>.85&&bounds.max.y<.95);
const {totalTriangleCount,totalVertexCount,drawCallCount}=k.info;
console.log(JSON.stringify({sha256:createHash('sha256').update(data).digest('hex'),bytes:data.length,issues:k.issues,triangles:totalTriangleCount,vertices:totalVertexCount,drawCalls:drawCallCount,meshes:json.meshes.length,materials:json.materials.length,panDepths,panRays:rays,rackApertures:apertures,bounds:[bounds.min.toArray(),bounds.max.toArray()]},null,2));

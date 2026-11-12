// Inspect actual exported geometry, transforms and clips; never infer successful export.
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';
import {Box3,Vector3,AnimationMixer} from 'three';
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';
import validator from 'gltf-validator';
const root=path.dirname(fileURLToPath(import.meta.url));
const file=path.join(root,'exports/gjh-mall-visitor.glb');
const bytes=fs.readFileSync(file);
const validation=await validator.validateBytes(new Uint8Array(bytes),{uri:path.basename(file)});
if(validation.issues.numErrors||validation.issues.numWarnings)throw Error(JSON.stringify(validation.issues));
const json=JSON.parse(bytes.subarray(20,20+bytes.readUInt32LE(12)));
if(json.images?.length||json.buffers.some(x=>x.uri)||json.extensionsRequired?.length)throw Error('Expected self-contained uncompressed texture-free model');
const gltf=await new GLTFLoader().parseAsync(bytes.buffer.slice(bytes.byteOffset,bytes.byteOffset+bytes.byteLength),'');
gltf.scene.updateMatrixWorld(true);
const bounds=new Box3().setFromObject(gltf.scene);let triangles=0,vertices=0,primitives=0;
gltf.scene.traverse(o=>{if(!o.isMesh)return;primitives++;vertices+=o.geometry.attributes.position.count;triangles+=(o.geometry.index?.count??o.geometry.attributes.position.count)/3;});
if(Math.abs(bounds.min.y)>.002||Math.abs(bounds.max.y-1.72)>.01)throw Error('Native floor/height contract failed');
if(bytes.length>2*1024*1024||triangles>15000||primitives>25)throw Error(`Budget exceeded: ${bytes.length} bytes, ${triangles} triangles, ${primitives} primitives`);
if(gltf.animations.map(c=>c.name).sort().join(',')!=='idle,sprint,walk')throw Error('Missing named clips');
const clips=[];
for(const clip of gltf.animations){
 for(const name of ['Body','LeftShoulder','RightShoulder','LeftElbow','RightElbow','LeftHip','RightHip','LeftKnee','RightKnee','LeftFoot','RightFoot']){
  for(const property of ['position','quaternion'])if(!clip.tracks.some(track=>track.name===`${name}.${property}`))throw Error(`${clip.name} omits reset channel ${name}.${property}`);
 }
 const mix=new AnimationMixer(gltf.scene);const action=mix.clipAction(clip);action.play();
 const joints=['LeftElbow','RightElbow','LeftKnee','RightKnee'];const rotations={};
 for(const name of joints)rotations[name]=[];
 const positions=[],footFloors=[];
 for(let i=0;i<=20;i++){
  mix.setTime(clip.duration*i/20);gltf.scene.updateMatrixWorld(true);
  positions.push(gltf.scene.getObjectByName('Body').position.toArray());
  let floor=Infinity;
  for(const name of ['LeftFoot','RightFoot'])gltf.scene.getObjectByName(name).traverse(o=>{
   if(!o.isMesh)return;const p=o.geometry.attributes.position;
   for(let j=0;j<p.count;j++)floor=Math.min(floor,new Vector3().fromBufferAttribute(p,j).applyMatrix4(o.matrixWorld).y);
  });
  footFloors.push(floor);
  for(const name of joints)rotations[name].push(gltf.scene.getObjectByName(name).quaternion.toArray());
 }
 const horizontal=Math.max(...[0,2].map(axis=>Math.max(...positions.map(p=>p[axis]))-Math.min(...positions.map(p=>p[axis]))));
 if(horizontal>1e-5)throw Error(`${clip.name} moves horizontally`);
 if(clip.name!=='idle')for(const [name,samples]of Object.entries(rotations))if(Math.max(...samples.map(q=>Math.abs(q[0]-samples[0][0])))<.01)throw Error(`${clip.name} missing ${name} articulation`);
 if(Math.max(...footFloors.map(Math.abs))>.012)throw Error(`${clip.name} loses foot contact: ${footFloors}`);
 clips.push({name:clip.name,duration:clip.duration,tracks:clip.tracks.length,horizontal_drift:horizontal,max_sole_floor_error:Math.max(...footFloors.map(Math.abs))});mix.stopAllAction();mix.uncacheRoot(gltf.scene);
}
const report={id:'gjh-mall-visitor',glb_bytes:bytes.length,sha256:createHash('sha256').update(bytes).digest('hex'),triangles,vertices,primitives,materials:json.materials.length,dimensions:bounds.getSize(new Vector3()).toArray(),bounds:{min:bounds.min.toArray(),max:bounds.max.toArray()},clips,validation:{errors:validation.issues.numErrors,warnings:validation.issues.numWarnings,validator:validation.validatorVersion}};
fs.writeFileSync(path.join(root,'reports/assets.json'),JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report,null,2));

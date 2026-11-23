// Runtime-structure check for a full character and matching standalone hair.
// Usage: node test_animation_module.mjs CHARACTER.glb HAIR.glb REPORT.json
// Requires Three.js 0.187.0 in THREE_DIR or /tmp/gjh-hair-three/node_modules/three.
// Texture decode is deliberately stubbed; this is not a browser/render test.
import fs from 'node:fs';
import crypto from 'node:crypto';
import { pathToFileURL } from 'node:url';
const [characterPath,hairPath,reportPath]=process.argv.slice(2);
if(!characterPath||!hairPath||!reportPath)throw Error('Expected character, hair and report paths');
const hash=p=>crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex');
const before={character:hash(characterPath),hair:hash(hairPath)};
const dir=process.env.THREE_DIR||'/tmp/gjh-hair-three/node_modules/three';
const THREE=await import(pathToFileURL(`${dir}/build/three.module.js`));
const {GLTFLoader}=await import(pathToFileURL(`${dir}/examples/jsm/loaders/GLTFLoader.js`));
globalThis.self??=globalThis;
globalThis.ProgressEvent??=class ProgressEvent {constructor(type,props={}){this.type=type;Object.assign(this,props);}};
const loader=new GLTFLoader();
loader.register(()=>({name:'NoTextureDecoder',loadTexture:()=>Promise.resolve(new THREE.Texture())}));
async function load(path){const bytes=fs.readFileSync(path);return loader.parseAsync(bytes.buffer.slice(bytes.byteOffset,bytes.byteOffset+bytes.byteLength),'');}
const [character,module]=await Promise.all([load(characterPath),load(hairPath)]);
character.scene.updateMatrixWorld(true);module.scene.updateMatrixWorld(true);
const heads=[],originals=[],replacements=[];
character.scene.traverse(o=>{if(o.isBone&&o.name==='Head')heads.push(o);if(o.isMesh&&o.userData.partSlot==='Hair')originals.push(o);});
module.scene.traverse(o=>{if(o.isMesh)replacements.push(o);});
if(heads.length!==1||originals.length!==1||replacements.length!==1)throw Error(`Expected one head, original hair and module mesh: ${heads.length}/${originals.length}/${replacements.length}`);
const [head]=heads,[original]=originals,[replacement]=replacements;
const headRest=character.scene.matrixWorld.clone().invert().multiply(head.matrixWorld);
head.add(module.scene);module.scene.matrixAutoUpdate=false;module.scene.matrix.copy(headRest.clone().invert());character.scene.updateMatrixWorld(true);
// Different exports may permute vertices after skin attributes are added. Build
// a nearest-vertex rest-space map with a spatial grid, resolving coincident seams
// by vertex colour. Reuse that map for every posed comparison.
function buildRestMap(){
 const a=original.geometry.attributes.position,b=replacement.geometry.attributes.position;
 if(!a||!b||a.count!==b.count)throw Error(`Different positions: ${a?.count} vs ${b?.count}`);
 const ca=original.geometry.attributes.color,cb=replacement.geometry.attributes.color;
 if(Boolean(ca)!==Boolean(cb))throw Error('Only one mesh has vertex colours');
 const cell=1e-4, grid=new Map(), pts=[];const p=new THREE.Vector3();
 function key(x,y,z){return `${x},${y},${z}`;}
 function colour(attr,i){if(!attr)return [];return [attr.getX(i),attr.getY(i),attr.getZ(i),attr.itemSize>3?attr.getW(i):1];}
 function colDiff(x,y){let z=0;for(let i=0;i<x.length;i++)z=Math.max(z,Math.abs(x[i]-y[i]));return z;}
 for(let i=0;i<b.count;i++){
  replacement.getVertexPosition(i,p);replacement.localToWorld(p);const v=p.clone(),k=v.toArray().map(x=>Math.floor(x/cell)),id=key(...k);
  if(!grid.has(id))grid.set(id,[]);grid.get(id).push(i);pts.push(v);
 }
 const map=[],dists=[],colors=[],originalPoints=[];
 for(let i=0;i<a.count;i++){
  original.getVertexPosition(i,p);original.localToWorld(p);originalPoints.push(p.clone());const k=p.toArray().map(x=>Math.floor(x/cell)),ac=colour(ca,i);let best=-1,bestColor=Infinity,bestDist=Infinity;
  for(let dx=-1;dx<=1;dx++)for(let dy=-1;dy<=1;dy++)for(let dz=-1;dz<=1;dz++)for(const j of grid.get(key(k[0]+dx,k[1]+dy,k[2]+dz))||[]){
   const d=p.distanceTo(pts[j]);if(d>=1e-5)continue;const cd=colDiff(ac,colour(cb,j));
   if(cd<bestColor-1e-8||(Math.abs(cd-bestColor)<=1e-8&&d<bestDist)){best=j;bestColor=cd;bestDist=d;}
  }
  if(best<0){for(let j=0;j<pts.length;j++){const d=p.distanceTo(pts[j]);if(d<bestDist){best=j;bestDist=d;bestColor=colDiff(ac,colour(cb,j));}}}map.push(best);dists.push(bestDist);colors.push(bestColor);
 }
 const reverseGrid=new Map();
 for(let i=0;i<originalPoints.length;i++){const v=originalPoints[i],id=key(...v.toArray().map(x=>Math.floor(x/cell)));if(!reverseGrid.has(id))reverseGrid.set(id,[]);reverseGrid.get(id).push(i);}
 let reverseMax=0;
 for(const v of pts){const k=v.toArray().map(x=>Math.floor(x/cell));let best=Infinity;for(let dx=-1;dx<=1;dx++)for(let dy=-1;dy<=1;dy++)for(let dz=-1;dz<=1;dz++)for(const i of reverseGrid.get(key(k[0]+dx,k[1]+dy,k[2]+dz))||[])best=Math.min(best,v.distanceTo(originalPoints[i]));if(best===Infinity)for(const q of originalPoints)best=Math.min(best,v.distanceTo(q));reverseMax=Math.max(reverseMax,best);}
 return {map,max_rest_mapping_error_m:Math.max(...dists),max_reverse_error_m:reverseMax,max_color_delta:Math.max(...colors)};
}
const mapping=buildRestMap();
function geometryComparison(){
 const a=original.geometry.attributes.position,b=replacement.geometry.attributes.position;
 if(!a||!b||a.count!==b.count)throw Error(`Different positions: ${a?.count} vs ${b?.count}`);
 const va=new THREE.Vector3(),vb=new THREE.Vector3();let max=0,sum=0;
 for(let i=0;i<a.count;i++){
  original.getVertexPosition(i,va);original.localToWorld(va);replacement.getVertexPosition(mapping.map[i],vb);replacement.localToWorld(vb);
  const d=va.distanceTo(vb);if(!Number.isFinite(d))throw Error('Non-finite vertex distance');max=Math.max(max,d);sum+=d;
 }
 return {vertices:a.count,max_m:max,mean_m:sum/a.count};
}
function colourComparison(){
 const a=original.geometry.attributes.color,b=replacement.geometry.attributes.color;
 if(!a&&!b)return {status:'absent_in_both'};
 if(!a||!b||a.count!==b.count||a.itemSize!==b.itemSize)return {status:'mismatch'};
 const mat1=Array.isArray(original.material)?original.material[0]:original.material;
 const mat2=Array.isArray(replacement.material)?replacement.material[0]:replacement.material;
 const matDelta=mat1.color&&mat2.color?Math.max(Math.abs(mat1.color.r-mat2.color.r),Math.abs(mat1.color.g-mat2.color.g),Math.abs(mat1.color.b-mat2.color.b)):null;
 return {status:'compared',max_vertex_component_delta:mapping.max_color_delta,max_material_color_delta:matDelta};
}
const threshold=1e-5,rest=geometryComparison(),colors=colourComparison();
const poses=[];
for(const deg of [[12,-17,8],[-25,20,-10],[20,25,0],[0,0,-25]]){
 head.rotation.set(...deg.map(x=>x*Math.PI/180));character.scene.updateMatrixWorld(true);poses.push({degrees:deg,...geometryComparison()});
}
head.rotation.set(0,0,0);character.scene.updateMatrixWorld(true);
const clips={};
for(const name of ['idle','walk','run','sit','stand_up']){
 const clip=character.animations.find(c=>c.name===name);if(!clip){clips[name]={status:'MISSING'};continue;}
 const mixer=new THREE.AnimationMixer(character.scene);const action=mixer.clipAction(clip);action.setLoop(THREE.LoopOnce,1);action.clampWhenFinished=true;action.play();
 const samples=[];
 for(const f of [0,.25,.5,.75,1]){const t=clip.duration*f;mixer.setTime(t);character.scene.updateMatrixWorld(true);samples.push({fraction:f,time_s:t,...geometryComparison()});}
 const movingTracks=clip.tracks.filter(t=>t.name.includes('Head')||t.name.includes('Spine')).length;
 clips[name]={status:'SAMPLED',duration_s:clip.duration,track_count:clip.tracks.length,head_or_spine_tracks:movingTracks,samples};
 action.stop();mixer.stopAllAction();mixer.uncacheRoot(character.scene);
}
original.visible=false;module.scene.visible=true;const swapped={original_visible:original.visible,replacement_visible:module.scene.visible};
original.visible=true;module.scene.visible=false;const restored={original_visible:original.visible,replacement_visible:module.scene.visible};
const all=[rest,...poses,...Object.values(clips).flatMap(c=>c.samples||[])];
const after={character:hash(characterPath),hair:hash(hairPath)};
const missing=Object.values(clips).some(c=>c.status!=='SAMPLED');
const pass=!missing&&mapping.max_reverse_error_m<threshold&&all.every(x=>x.max_m<threshold)&&JSON.stringify(before)===JSON.stringify(after)&&!swapped.original_visible&&swapped.replacement_visible&&restored.original_visible&&!restored.replacement_visible&&colors.status!=='mismatch'&&(colors.max_vertex_component_delta??0)<=1e-5&&(colors.max_material_color_delta??0)<=1e-5;
const report={status:pass?'PASS':'FAIL',three:'0.187.0',sha256:before,inputs_unchanged:JSON.stringify(before)===JSON.stringify(after),threshold_m:threshold,rest_mapping_max_m:mapping.max_rest_mapping_error_m,rest_mapping_reverse_max_m:mapping.max_reverse_error_m,character_hair:original.name,standalone_hair:replacement.name,head:head.name,rest,head_poses:poses,clips,colors,swapped,restored,limitations:['Three.js GLTFLoader with texture decoder stubbed in Node; no browser, image texture decode, WebGL or rendered visual check.','Five evenly spaced samples per clip and four head rotations; this does not establish continuous motion or floor contact.','Rest vertices are matched spatially and by colour before comparison; texture decoding, topology equality and normals are not validated.']};
fs.writeFileSync(reportPath,JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify({status:report.status,sha256:before,rest:rest.max_m,poses:poses.map(x=>x.max_m),clips:Object.fromEntries(Object.entries(clips).map(([k,v])=>[k,{status:v.status,max_m:Math.max(...(v.samples||[]).map(x=>x.max_m))}])),colors}));
if(!pass)process.exitCode=1;

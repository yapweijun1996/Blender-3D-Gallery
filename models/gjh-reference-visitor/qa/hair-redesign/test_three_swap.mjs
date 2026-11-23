// Node geometry/rig test. No WebGL, browser, or texture rendering is exercised.
// Setup: npm install --prefix /tmp/gjh-hair-three --no-audit --no-fund three@0.187.0
// Set THREE_DIR to another installed three package directory if desired.
import fs from 'node:fs';
import crypto from 'node:crypto';
import { pathToFileURL } from 'node:url';
const threeDir = process.env.THREE_DIR || '/tmp/gjh-hair-three/node_modules/three';
const THREE = await import(pathToFileURL(`${threeDir}/build/three.module.js`));
const { GLTFLoader } = await import(pathToFileURL(`${threeDir}/examples/jsm/loaders/GLTFLoader.js`));
if (!globalThis.self) globalThis.self = globalThis;
if (!globalThis.ProgressEvent) globalThis.ProgressEvent = class ProgressEvent { constructor(type, props={}) {this.type=type;Object.assign(this,props)} };
const base='/Users/yapweijun/Documents/GitHub/Blender-3D-Gallery/models/gjh-reference-visitor';
const characterFile=`${base}/exports/gjh-reference-visitor-rigged.glb`;
const moduleFile=`${base}/exports/gjh-visitor-hair.glb`;
const hash = p => crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex');
const sha256={character:hash(characterFile),module:hash(moduleFile)};
const loader=new GLTFLoader();
// Test geometry and hierarchy without requiring browser image decoders.
loader.register(() => ({name:'NoTextureDecoder', loadTexture:()=>Promise.resolve(new THREE.Texture())}));
const load = async path => {const b=fs.readFileSync(path);return loader.parseAsync(b.buffer.slice(b.byteOffset,b.byteOffset+b.byteLength),'');};
const character=await load(characterFile), hair=await load(moduleFile);
character.scene.updateMatrixWorld(true);hair.scene.updateMatrixWorld(true);
let head,original,replacement;
character.scene.traverse(o=>{if(o.isBone && o.name==='Head')head=o;if(o.isMesh && o.userData.partSlot==='Hair')original=o;});
hair.scene.traverse(o=>{if(o.isMesh)replacement=o;});
if(!head||!original||!replacement)throw new Error('Missing head or hair node');
const headRestInModel=character.scene.matrixWorld.clone().invert().multiply(head.matrixWorld);
head.add(hair.scene);hair.scene.matrixAutoUpdate=false;hair.scene.matrix.copy(headRestInModel.invert());
character.scene.updateMatrixWorld(true);
function check(){
 const n=original.geometry.attributes.position.count;
 if(n!==replacement.geometry.attributes.position.count)throw Error('Different vertex counts');
 let max=0,sum=0;const a=new THREE.Vector3(),b=new THREE.Vector3();
 for(let i=0;i<n;i++){
   original.getVertexPosition(i,a);original.localToWorld(a);
   replacement.getVertexPosition(i,b);replacement.localToWorld(b);
   const d=a.distanceTo(b);max=Math.max(max,d);sum+=d;
 }
 return {vertices:n,max_m:max,mean_m:sum/n};
}
const rest=check();
head.rotation.set(12*Math.PI/180,-17*Math.PI/180,8*Math.PI/180);
character.scene.updateMatrixWorld(true);const rotated=check();
original.visible=false;hair.scene.visible=true;
const swapped={original_visible:original.visible,replacement_visible:hair.scene.visible};
original.visible=true;hair.scene.visible=false;
const restored={original_visible:original.visible,replacement_visible:hair.scene.visible};
const pass=rest.max_m<1e-5 && rotated.max_m<1e-5 && !swapped.original_visible && swapped.replacement_visible && restored.original_visible && !restored.replacement_visible;
const report={status:pass?'PASS':'FAIL',three:'0.187.0',sha256,character_hair_node:original.name,head:head.name,module_mesh:replacement.name,rest,rotated,head_rotation_degrees:[12,-17,8],swapped,restored,limitations:['Three.js GLTFLoader and skin math tested in Node with texture decoding stubbed; no rendering or browser tested.','One rotated pose only; no animation playback or full-cycle check.']};
fs.writeFileSync(`${base}/qa/hair-redesign/three-swap-test.json`,JSON.stringify(report,null,2)+'\n');
console.log(JSON.stringify(report));if(!pass)process.exitCode=1;

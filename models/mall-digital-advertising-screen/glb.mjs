import fs from 'node:fs';import assert from 'node:assert/strict';import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';
export const near=(a,b,tol=1e-6)=>assert.ok(Math.abs(a-b)<tol,`${a} != ${b}`);
// Geometry-only Node parsing. Actual PNG decode is checked by Pillow and real browser pixels.
globalThis.self=globalThis;globalThis.createImageBitmap=async()=>({width:1024,height:576,close(){}});
export async function readGlb(file){const bytes=fs.readFileSync(file),json=JSON.parse(bytes.subarray(20,20+bytes.readUInt32LE(12)));const gltf=await new GLTFLoader().parseAsync(bytes.buffer.slice(bytes.byteOffset,bytes.byteOffset+bytes.byteLength),'');gltf.scene.updateMatrixWorld(true);return {bytes,json,scene:gltf.scene};}
export function embeddedImage(bytes,json,i=0){const offset=20+bytes.readUInt32LE(12)+8,v=json.bufferViews[json.images[i].bufferView];return bytes.subarray(offset+(v.byteOffset||0),offset+(v.byteOffset||0)+v.byteLength);}

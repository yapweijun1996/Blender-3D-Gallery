import assert from 'node:assert/strict';
import fs from 'node:fs';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
// Node structural loader: PNG dimensions are checked here, not rendered. Actual
// decoded pixels are separately verified with Pillow and in Chromium/WebGL.
globalThis.self ??= globalThis;
globalThis.createImageBitmap ??= async blob => {
 const b=Buffer.from(await blob.arrayBuffer());assert.equal(b.toString('hex',0,8),'89504e470d0a1a0a');
 return {width:b.readUInt32BE(16),height:b.readUInt32BE(20),close(){}};
};
export const near=(a,b)=>assert.ok(Math.abs(a-b)<1e-6,`${a} != ${b}`);
export async function readGlb(file){
 const bytes=fs.readFileSync(file),json=JSON.parse(bytes.subarray(20,20+bytes.readUInt32LE(12)));
 const gltf=await new GLTFLoader().parseAsync(bytes.buffer.slice(bytes.byteOffset,bytes.byteOffset+bytes.byteLength),'');
 gltf.scene.updateMatrixWorld(true);return {bytes,json,scene:gltf.scene};
}

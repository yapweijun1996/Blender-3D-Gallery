import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import { createHash } from 'node:crypto';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { Vector3, Texture, Box3, PerspectiveCamera } from 'three';
import { fitProductDistance, VIEW_DIRECTIONS, setProductView } from '../src/product-studio/camera.js';
import { createPoseController } from '../src/product-studio/pose.js';

test('actual demo tin authored clips retain world-space motion, grip hierarchy and exact reset', async () => {
 const bytes=fs.readFileSync('models/demo-food-tin/exports/demo-food-tin.glb');
 assert.equal(createHash('sha256').update(bytes).digest('hex'),'4b265f78a711d95a80b730ebeaae3906f42c93fbd28f0b8c6e64c8c003eee0ee');
 // Node pose-only test: skip image decoding; the browser gate validates actual texture pixels.
 const loader=new GLTFLoader().register(()=>({name:'POSE_ONLY_TEXTURE',loadTexture:()=>Promise.resolve(new Texture())}));
 const gltf=await loader.parseAsync(bytes.buffer.slice(bytes.byteOffset,bytes.byteOffset+bytes.byteLength),'');
 const control=createPoseController(gltf), lid=gltf.scene.getObjectByName('MOVABLE_Lid'), ring=gltf.scene.getObjectByName('MOVABLE_PullRing');
 assert.equal(ring.parent,lid);
 const world=n=>n.getWorldPosition(new Vector3()).toArray();
 const snapshot=()=>{gltf.scene.updateMatrixWorld(true);const a=[];gltf.scene.traverse(n=>a.push([n.name,...n.matrixWorld.elements]));return a;};
 control.apply('closed');const rest=snapshot(),l0=world(lid),r0=world(ring);
 for(let repeat=0;repeat<4;repeat++) for(const mode of ['open','exploded']) {
  let prior=0;
  for(let i=0;i<=60;i++) {
   control.apply(mode,i/60);const l=world(lid),r=world(ring);
   assert.ok(Math.abs(l[0]-l0[0])<1e-7&&Math.abs(l[2]-l0[2])<1e-7);
   const dy=l[1]-l0[1];assert.ok(dy>=prior-1e-7);prior=dy;
   if(i===60){assert.ok(Math.abs(dy-(mode==='open'?.045:.070))<1e-6);assert.ok(Math.abs(r[1]-r0[1]-(mode==='open'?.045:.095))<1e-6);}
  }
  for(let i=60;i>=0;i--)control.apply(mode,i/60);
  control.apply('closed');assert.deepEqual(snapshot(),rest);
 }
 control.apply('open');control.apply('exploded');control.apply('closed');assert.deepEqual(snapshot(),rest);
 const bounds=new Box3();for(const mode of ['closed','open','exploded']){control.apply(mode);bounds.union(new Box3().setFromObject(gltf.scene));}
 const center=bounds.getCenter(new Vector3()),radius=bounds.getSize(new Vector3()).length()/2;
 for(const [width,height] of [[1018,560],[370,560],[356,340],[286,340],[510,340]]) {
  const camera=new PerspectiveCamera(35,width/height,radius/80,radius*80);
  for(const direction of Object.values(VIEW_DIRECTIONS)) {
   camera.position.copy(center).add(new Vector3(...direction).normalize().multiplyScalar(fitProductDistance(radius,width/height)));camera.lookAt(center);camera.updateMatrixWorld(true);
   for(const mode of ['open','exploded'])for(let sample=0;sample<=20;sample++) {
    control.apply(mode,sample/20);gltf.scene.traverse(n=>{if(!n.isMesh)return;const a=n.geometry.getAttribute('position');for(let i=0;i<a.count;i++){
     const p=new Vector3().fromBufferAttribute(a,i).applyMatrix4(n.matrixWorld).project(camera);
     assert.ok(Math.abs(p.x)<1-8/width&&Math.abs(p.y)<1-8/height&&p.z>-1&&p.z<1,'actual exported vertex fits with >4px margin');
    }});
   }
  }
 }
 control.dispose();
});

test('production camera reset restores exact position, zoom and target after arbitrary orbit',()=>{
 const camera=new PerspectiveCamera(35,356/340,.001,10), center=new Vector3(0,.12,0);
 const controls={target:new Vector3(),update(){camera.lookAt(this.target);camera.updateMatrixWorld(true);}};
 const snapshot=()=>({position:camera.position.toArray(),quaternion:camera.quaternion.toArray(),zoom:camera.zoom,target:controls.target.toArray(),projection:camera.projectionMatrix.toArray()});
 setProductView(camera,controls,center,.4,'front');const initial=snapshot();
 for(const name of Object.keys(VIEW_DIRECTIONS)) {
  setProductView(camera,controls,center,.4,name);camera.zoom=2;camera.position.set(1,2,3);controls.target.set(4,5,6);
  setProductView(camera,controls,center,.4,'front');assert.deepEqual(snapshot(),initial);
 }
});

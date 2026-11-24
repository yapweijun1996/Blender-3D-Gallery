import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { validateBytes } from 'gltf-validator';
import { Raycaster, Vector3 } from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';

const slug='roadside-catchpit-cutaway';
const p=new URL('./exports/'+slug+'.glb',import.meta.url);
const data=await readFile(p);
const valid=await validateBytes(new Uint8Array(data),{uri:slug+'.glb',maxIssues:1000});
assert.equal(valid.issues.numErrors,0,JSON.stringify(valid.issues));
assert.equal(valid.issues.numWarnings,0,JSON.stringify(valid.issues));
const glb=JSON.parse(data.subarray(20,20+data.readUInt32LE(12)));
assert.equal(glb.asset.version,'2.0');
assert.deepEqual(glb.buffers.map(b=>b.uri),[undefined]);
assert.equal(glb.images?.length??0,0);
assert.equal(glb.textures?.length??0,0);
assert.equal(glb.animations?.length??0,0);
assert.equal(glb.cameras?.length??0,0);
assert.equal(glb.extensions?.KHR_lights_punctual?.lights?.length??0,0);
const doc=await new GLTFLoader().parseAsync(data.buffer.slice(data.byteOffset,data.byteOffset+data.byteLength),'');
assert.equal(doc.animations.length,0);
const scene=doc.scene;scene.updateMatrixWorld(true);
const world=(x,y,z)=>new Vector3(x,z,-y);
const ray=new Raycaster();
let samples=0;
function cast(start,direction,prefix,test,far=3) {
  ray.set(world(...start),world(...direction));
  ray.far=far;
  const first=ray.intersectObject(scene,true)[0];
  assert.ok(first,JSON.stringify(start));
  assert.ok([prefix].flat().some(n=>first.object.name.startsWith(n)),JSON.stringify([start,direction,prefix,first.object.name,first.point]));
  assert.ok(test(first.point));
  samples++;
}
for(let i=0;i<9;i++)for (const y of [-.266,-.205,-.145]) {
  cast([-.565+i*.0615,y,1.30],[0,0,-1],'Distinct_crossbar',p=>p.y>.934&&p.y<.938);
}
for(let i=0;i<8;i++)for (const y of [-.266,-.205,-.145]) {
  cast([-.565+(i+.5)*.0615,y,1.30],[0,0,-1],'Thin_illustrative_sump',p=>p.y>.173&&p.y<.177);
}
for (const x of [-.50,-.31,-.10]) {
  cast([x,-.405,.973],[0,1,0],'Small_rim_collar',p=>p.z<-.244&&p.z>-.250);
  cast([x,.150,.999],[0,0,-1],'Thin_illustrative_sump',p=>p.y>.173&&p.y<.177);
  cast([x,-.565,.510],[0,1,0],'Rear_chamber_backing_wall',p=>p.z<-.432&&p.z>-.442);
}
for(const radius of [.025,.069,.091,.118]) for(let i=0;i<16;i++) {
  const t=i*Math.PI/8;
  cast([.864,.063+radius*Math.cos(t),.385+radius*Math.sin(t)],[-1,0,0],
    ['Left_full-height_cast_retaining_wall','Raised_seam_in_left_chamber'],p=>p.x<-.715&&p.x>-.735);
}
const info=valid.info;
console.log(JSON.stringify({sha256:createHash('sha256').update(data).digest('hex'),bytes:data.length,
  issues:valid.issues,triangles:info.totalTriangleCount,vertices:info.totalVertexCount,drawCalls:info.drawCallCount,
  meshes:glb.meshes.length,materials:glb.materials.length,browserEngineRayChecks:samples},null,2));

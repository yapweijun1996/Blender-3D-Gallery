// Run from the repository root. Verify the exported surfaces and repeat joints in metres.
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import fs from 'node:fs/promises';
import { createRequire } from 'node:module';
import { dirname, resolve } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const asset = dirname(fileURLToPath(import.meta.url));
const project = createRequire(resolve('package.json'));
const { Box3, Raycaster, Vector3 } = await import(new URL('three.module.js', pathToFileURL(project.resolve('three'))).href);
const { validateBytes } = project('gltf-validator');
const { readGlb } = await import(pathToFileURL(resolve('models/mall-floor-tile/glb.mjs')).href);
const threshold = 1e-6;

function near(a, b, label) {
  assert.ok(Math.abs(a-b)<threshold, `${label}: expected ${b}, measured ${a}`);
}

function face(scene, x, y, back = false) {
  const z = back ? -1 : 1;
  const ray = new Raycaster(new Vector3(x, y, z), new Vector3(0, 0, -z), 0, 2);
  return ray.intersectObject(scene,true)[0]?.point.z;
}

function at(scene, x) {
  const copy = scene.clone(true);
  copy.position.x = x;
  copy.updateMatrixWorld(true);
  return copy;
}

function shape(scene, level) {
  const box = new Box3().setFromObject(scene, true);
  for (const [actual, expected] of [[box.min,[-1,0,-.075]],[box.max,[1,2.8,.075]]]) {
    actual.toArray().forEach((n,i)=>near(n,expected[i],`${level} bounds`));
  }
  for (const [name,x] of [['Left',-1],['Right',1]]) {
    const socket = scene.getObjectByName(`CONNECTOR_${name}_${level}`);
    assert.ok(socket);
    const p = socket.getWorldPosition(new Vector3());
    near(p.x,x,'connector X'); near(p.y,0,'connector height'); near(p.z,0,'connector depth');
  }
  return box;
}

function seams(scene, level) {
  const instances = [-2,0,2].map(x=>at(scene,x));
  const data = [];
  for (const i of [0,1]) {
    const boundary = i === 0 ? -1 : 1;
    const pair = instances.slice(i,i+2);
    const boxes = pair.map(o=>new Box3().setFromObject(o,true));
    const gap = boxes[1].min.x - boxes[0].max.x;
    near(gap,0,'end planes');
    let largestMismatch = 0, samples = 0;
    for (const [height, front] of [[.06,.075],[.11,.075],[.65,.072],[1.9,.072],[2.76,.075]]) {
      for (const offset of [.0005,.004,.02]) {
        const left = face(pair[0],boundary-offset,height);
        const right = face(pair[1],boundary+offset,height);
        const panel = height>.12 && height<2.73;
        const expected = level!=='LOD2' && panel && offset<.002 ? .062 : front;
        near(left,expected,'left face profile');
        near(right,expected,'right face profile');
        near(face(pair[0],boundary-offset,height,true),-.075,'left back');
        near(face(pair[1],boundary+offset,height,true),-.075,'right back');
        largestMismatch=Math.max(largestMismatch,Math.abs(right-left));
        samples+=4;
      }
    }
    if (level!=='LOD2') {
      for (const x of [boundary-.05, boundary+.05]) {
        const host=x<boundary?pair[0]:pair[1];
        near(face(host,x,1.43),.062,'course shadow joint');
        near(face(host,x,.124),.062,'plinth shadow joint');
        near(face(host,x,2.729),.062,'upper shadow joint');
        samples+=3;
      }
    }
    data.push({boundaryX:boundary,gapM:gap,largestPairedFrontDifferenceM:largestMismatch,surfaceHits:samples});
  }
  // Restore the 5 mm placement error and reversed interior orientation on separate clones.
  const shifted=at(scene,2.005);
  assert.equal(face(instances[1],1.0025,.65),undefined);
  assert.equal(face(shifted,1.0025,.65),undefined);
  const turned=at(scene,2);
  turned.rotation.y=Math.PI;
  turned.updateMatrixWorld(true);
  const wrong=face(turned,1.025,.65);
  assert.ok(Math.abs(wrong-.072)>.002);
  return data;
}

const fileNames=['mall-wall-module-2m.glb','mall-wall-module-2m-lod1.glb','mall-wall-module-2m-lod2.glb'];
const report={thresholdM:threshold,levels:{}};
let previous;
for (const [i,name] of fileNames.entries()) {
  const level='LOD'+i;
  const {bytes,json,scene}=await readGlb(resolve(asset,'exports',name));
  const result=await validateBytes(bytes,{uri:name,maxIssues:100});
  assert.equal(result.issues.numErrors,0,JSON.stringify(result.issues.messages));
  assert.equal(result.issues.numWarnings,0,JSON.stringify(result.issues.messages));
  const extras=[];
  JSON.stringify(json,(key,value)=>{ if (key==='extras') extras.push(value); return value; });
  assert.deepEqual(extras,[{backlog_id:'MALL-STR-010',pitch_m:2,front:'glTF +Z. Ground-centre pivot in metres.'}]);
  assert.equal(json.buffers.length,1);
  assert.equal(json.buffers[0].uri,undefined);
  assert.equal(json.animations,undefined); assert.equal(json.cameras,undefined);
  const images=json.images || [];
  assert.equal(images.length,level==='LOD0'?1:0);
  for (const image of images) { assert.equal(image.mimeType,'image/png'); assert.equal(image.uri,undefined); }
  const primitives=json.meshes.flatMap(mesh=>mesh.primitives);
  const triangles=primitives.reduce((sum,p)=>sum+json.accessors[p.indices].count/3,0);
  const draws=primitives.length;
  if (previous) {
    assert.ok(triangles<previous.triangles && draws<previous.draws && bytes.length<previous.bytes);
  }
  if (level==='LOD2') {
    assert.equal(draws,1); assert.ok(primitives[0].attributes.COLOR_0!==undefined);
  }
  if (level==='LOD0') {
    const paint=json.materials.findIndex(m=>m.pbrMetallicRoughness?.baseColorTexture);
    assert.ok(paint>=0 && primitives.filter(p=>p.material===paint).length===8);
  }
  const bounds=shape(scene,level), joins=seams(scene,level);
  const stats={sha256:createHash('sha256').update(bytes).digest('hex'),bytes:bytes.length,triangles,draws,
    validator:{errors:0,warnings:0},bounds:{min:bounds.min.toArray(),max:bounds.max.toArray()},straightJoins:joins};
  report.levels[level]=stats;
  previous=stats;
}
report.negativeControls=['Gap between run sections increased to 5 mm','Right section rotated outward'];
report.result='pass';
await fs.mkdir(resolve(asset,'reports'),{recursive:true});
await fs.writeFile(resolve(asset,'reports/geometry.json'),JSON.stringify(report,null,2)+'\n');
console.log(JSON.stringify(report));

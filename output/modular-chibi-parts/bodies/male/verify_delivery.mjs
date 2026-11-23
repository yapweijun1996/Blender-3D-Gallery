import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import fs from 'node:fs';

const read = name => fs.readFileSync(new URL(name,import.meta.url));
const json = name => JSON.parse(read(name));
const hash = data => createHash('sha256').update(data).digest('hex');
const check = json('qa/khronos.json');
const renders = json('renders/manifest.json');
const runtime = json('qa/demo_runtime_smoke.json');
const durations = json('qa/clip_durations.json');
const body = json('qa/body_selfcheck.json');
const floor = json('qa/floor_validation.json');
const outfit = json('qa/outfit_layer_reimport.json');
const modules = ['hair-bob','hair-spiky','hair-sidepart','tshirt','dress','jeans','sneakers'];
const jointBanks = ['body_male.glb','motion_male.glb','hand_gestures_male.glb'];
const delivery = { files:{}, poses:{}, verification:{}, views:0 };

for (const file of [...jointBanks,...modules.map(key=>`male-${key}.glb`)]) {
  const value = check[file];
  assert.equal(hash(read(file)),value.sha256,file);
  assert.equal(value.joints,65,file);
  assert.equal(value.hierarchyMatchesNeutral,true,file);
  assert.equal(value.validator.issues.numErrors,0,file);
  assert(value.images.every(img=>Math.max(...img.size)<=1024),file);
  delivery.files[file] = { bytes:value.bytes, triangles:value.triangles, sha256:value.sha256,
    khronosWarnings:value.validator.issues.numWarnings };
}
const skin = check['body_male.glb'];
assert.deepEqual(skin.skinnedNodes,['Base_Body']);
assert(skin.bytes<=1.2*1048576 && skin.triangles<=10000);
assert(Math.abs(skin.bounds[1][0])<1.e-6);
for (const file of jointBanks) assert.equal(check[file].validator.issues.numWarnings,0,file);
assert.equal(Object.keys(check['motion_male.glb'].animations).length,14);
for (const [name,duration] of Object.entries(durations)) {
  const actual = check['motion_male.glb'].animations[name];
  assert(actual && actual.duration===duration && actual.channels.rotation===65,name);
}
const rawGestures = read('../../studio-modules/body-male/work/hand_gestures_male.glb');
assert.equal(hash(rawGestures),check['hand_gestures_male.glb'].sha256);
assert.equal(runtime.gestureNames.length,18);
assert.equal(runtime.clipNames.length,14);
assert.equal(Object.keys(body.clips).length,14);
assert.equal(Object.keys(floor.clips).length,14);
assert.equal(renders.body_sha256,check['body_male.glb'].sha256);
assert.equal(renders.motion_sha256,check['motion_male.glb'].sha256);
assert.equal(renders.outfits.sha256,hash(read(renders.outfits.file)));
for (const key of modules) {
  const file = `male-${key}.glb`;
  const model = check[file];
  const record = json(`qa/direct/male-${key}.json`);
  const view = renders.modules[key];
  assert(model.bytes<=1.5*1048576,file);
  assert(model.triangles<= (key.startsWith('hair')?3000:key==='sneakers'?3500:6000),file);
  assert.equal(view.sha256,model.sha256,file);
  assert.equal(record.sha256,model.sha256,file);
  assert.equal(record.motion_sha256,check['motion_male.glb'].sha256,file);
  assert.equal(Object.keys(record.clips).length,15,file);
  assert(runtime.moduleMeshes[file]>0,file);
  assert.equal(view.views.length,6,file);
  assert.equal(new Set(view.views).size,6,file);
  for (const image of view.views) {
    const png = read(image);
    assert.equal(png.readUInt32BE(16),renders.resolution[0],image);
    assert.equal(png.readUInt32BE(20),renders.resolution[1],image);
    delivery.views++;
  }
  const posed = Object.values(record.clips);
  const inside = Math.max(...posed.map(r=>r.max_vertices_inside));
  const overlap = Math.max(...posed.map(r=>r.max_tri_pairs));
  const signed = Math.min(...posed.map(r=>r.minimum_m));
  delivery.poses[key] = { maxVerticesInside:inside, maxTrianglePairs:overlap, minimumSignedM:signed,
    passed: inside===0 && overlap===0 && signed>=.0005 };
}
assert.equal(delivery.views,42);
for (const slot of ['tshirt','jeans']) assert.equal(outfit.assets[slot],check[`male-${slot}.glb`].sha256);
delivery.verification = {
  bodyPassClips:Object.entries(body.clips).filter(([,row])=>row.total_pairs===0).map(([name])=>name),
  bodyOverlapOccurrences:Object.values(body.clips).reduce((sum,row)=>sum+row.total_pairs,0),
  floorMaxErrorMm:floor.maxErrorMm, outfitLayerTrianglePairs:outfit.clips,
  outfitContactSheetSha256:renders.outfits.sha256,
  masterSha256:hash(read('master_male.blend')),
};
fs.writeFileSync(new URL('qa/delivery.json',import.meta.url),JSON.stringify(delivery,null,2)+'\n');
console.log(`Checked ${Object.keys(delivery.files).length} GLBs and ${delivery.views} views.`);
console.log(delivery.poses);

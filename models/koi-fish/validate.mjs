import assert from 'node:assert/strict';
import fs from 'node:fs';
import {createHash} from 'node:crypto';
import {fileURLToPath} from 'node:url';
import {AnimationMixer, Box3, LoopOnce, Vector3} from 'three';
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';
import validator from 'gltf-validator';

const dir = fileURLToPath(new URL('.', import.meta.url));
async function load(file) {
  const bytes = fs.readFileSync(file);
  const json = JSON.parse(bytes.subarray(20, 20 + bytes.readUInt32LE(12)));
  const gltf = await new GLTFLoader().parseAsync(bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength), '');
  gltf.scene.updateMatrixWorld(true);
  return {bytes, json, gltf};
}
const {bytes, json, gltf} = await load(dir + 'exports/optimized.glb');
const validation = await validator.validateBytes(new Uint8Array(bytes));
fs.writeFileSync(dir + 'reports/khronos.json', JSON.stringify(validation, null, 2) + '\n');
assert.equal(validation.issues.numErrors, 0);
assert.equal(validation.issues.numWarnings, 0);
assert.ok(json.buffers.every(b => !b.uri));
assert.ok(!json.images?.length && !json.textures?.length && !json.cameras?.length);
assert.ok(!json.extensions?.KHR_lights_punctual);
assert.equal(json.materials.length, 3);
assert.equal(json.meshes.length, 1);
assert.equal(json.skins.length, 1);
const primitives = json.meshes.flatMap(m => m.primitives).length;
assert.equal(primitives, 3);
const root = gltf.scene.getObjectByName('ASSET_KoiFish');
assert.ok(root);
assert.deepEqual(root.position.toArray(), [0, 0, 0]);
assert.equal(root.userData.units, 'metres');
assert.equal(root.userData.front_axis, 'Blender -Y / glTF +Z');
assert.equal(gltf.animations.length, 1);
const clip = gltf.animations[0];
assert.equal(clip.name, 'Swim_Loop');
const start = Math.min(...clip.tracks.map(t => t.times[0]));
const end = Math.max(...clip.tracks.map(t => t.times.at(-1)));
assert.ok(Math.abs(end - start - 3) < 1e-6);
for (const track of clip.tracks) {
  const size = track.getValueSize();
  for (let i = 0; i < size; i++)
    assert.ok(Math.abs(track.values[i] - track.values.at(-size + i)) < 1e-6, 'cyclic channel endpoints');
  assert.ok(!track.name.startsWith('ASSET_KoiFish.'), 'no trajectory animation');
}
const meshes = [];
gltf.scene.traverse(o => { if (o.isMesh) meshes.push(o); });
let triangles = 0, vertices = 0;
for (const mesh of meshes) {
  assert.ok(mesh.isSkinnedMesh);
  const g = mesh.geometry, p = g.attributes.position, index = g.index;
  assert.ok(g.attributes.normal && g.attributes.color && g.attributes.skinWeight && g.attributes.skinIndex);
  for (const name of ['position', 'normal', 'color', 'skinWeight'])
    assert.ok([...g.attributes[name].array].every(Number.isFinite));
  for (const color of g.attributes.color.array) assert.ok(color >= 0 && color <= 1);
  for (let i = 0; i < p.count; i++) {
    let total = 0;
    for (let j = 0; j < 4; j++) total += g.attributes.skinWeight.getComponent(i, j);
    assert.ok(Math.abs(total - 1) < 1e-5, 'normalized skin weights');
  }
  const count = index?.count ?? p.count;
  const a = new Vector3(), b = new Vector3(), c = new Vector3();
  for (let i = 0; i < count; i += 3) {
    a.fromBufferAttribute(p, index ? index.getX(i) : i);
    b.fromBufferAttribute(p, index ? index.getX(i + 1) : i + 1);
    c.fromBufferAttribute(p, index ? index.getX(i + 2) : i + 2);
    assert.ok(b.sub(a).cross(c.sub(a)).lengthSq() > 1e-25, 'nondegenerate exported triangle');
  }
  triangles += count / 3;
  vertices += p.count;
}
assert.ok(triangles < 20000);
assert.ok(bytes.length < 1.5 * 1024 * 1024);
const mixer = new AnimationMixer(gltf.scene);
const action = mixer.clipAction(clip).setLoop(LoopOnce, 1);
action.clampWhenFinished = true;
action.play();
function sample(time) {
  mixer.setTime(time);
  gltf.scene.updateMatrixWorld(true);
  for (const mesh of meshes) mesh.skeleton.update();
  return meshes.flatMap(mesh => {
    const points = [];
    for (let i = 0; i < mesh.geometry.attributes.position.count; i++)
      points.push(mesh.getVertexPosition(i, new Vector3()).applyMatrix4(mesh.matrixWorld));
    return points;
  });
}
const initial = sample(start);
const bounds = new Box3().setFromPoints(initial);
const dimensions = bounds.getSize(new Vector3()).toArray();
assert.ok(Math.abs(dimensions[2] - .30) < .001, 'approximately 0.30 m long');
assert.ok(Math.abs(bounds.min.y) < 1e-6, 'reference pose floor datum');
assert.ok(Math.abs(bounds.min.x + bounds.max.x) < 1e-6, 'centred width');
assert.ok(Math.abs(bounds.min.z + bounds.max.z) < 1e-6, 'centred depth');
let tailMotion = 0, bodyMotion = 0, headMotion = 0, loopError = 0;
const swimBounds = bounds.clone();
for (let phase = 0; phase <= 24; phase++) {
  const points = sample(start + (end - start) * phase / 24);
  for (let i = 0; i < points.length; i++) {
    swimBounds.expandByPoint(points[i]);
    const displacement = points[i].distanceTo(initial[i]);
    if (initial[i].z < -.10) tailMotion = Math.max(tailMotion, displacement);
    if (Math.abs(initial[i].z) < .04) bodyMotion = Math.max(bodyMotion, displacement);
    if (initial[i].z > .12) headMotion = Math.max(headMotion, displacement);
    if (phase === 24) loopError = Math.max(loopError, displacement);
  }
}
assert.ok(tailMotion > .005, 'visible deformed tail motion');
assert.ok(bodyMotion > .0005, 'deformed body motion');
assert.ok(headMotion < .0001, 'head remains stable, no root trajectory');
assert.ok(loopError < 1e-6, 'deformed mesh loop closure');
let sourceEdit = 'NOT RUN';
if (process.argv.includes('--source-edit')) {
  const edited = await load('/tmp/koi-fish-source-edit.glb');
  const editedBounds = new Box3().setFromObject(edited.gltf.scene, true);
  assert.ok(editedBounds.min.z < bounds.min.z - .0015, 'controlled tail edit survives export');
  assert.equal(edited.gltf.animations[0].name, clip.name);
  assert.equal(edited.json.materials.length, 3);
  sourceEdit = 'PASS controlled tail edit exported from reopened source without saving it';
}
const report = {result: 'PASS', id: 'koi-fish', glb_bytes: bytes.length,
  triangles, vertices, mesh_definitions: json.meshes.length, rendered_mesh_nodes: meshes.length,
  primitives, materials: json.materials.length, images: 0, animations: gltf.animations.length,
  dimensions, dimensions_order: 'glTF X,Y,Z (width,height,length), metres',
  bounds: {min: bounds.min.toArray(), max: bounds.max.toArray()},
  sampled_swim_bounds: {min: swimBounds.min.toArray(), max: swimBounds.max.toArray(), samples: 25},
  clip: {name: clip.name, start_seconds: start, end_seconds: end, period_seconds: end - start,
    tail_displacement_m: tailMotion, body_displacement_m: bodyMotion, head_displacement_m: headMotion,
    endpoint_error_m: loopError, root_motion: false},
  validation: {errors: validation.issues.numErrors, warnings: validation.issues.numWarnings},
  source_edit: sourceEdit, sha256: createHash('sha256').update(bytes).digest('hex'),
  limitations: '25 sampled poses; no continuous collision, water simulation or full mall performance claim.'};
fs.writeFileSync(dir + 'reports/assets.json', JSON.stringify(report, null, 2) + '\n');
console.log(JSON.stringify(report, null, 2));

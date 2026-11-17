// Independently inspect the delivered GLB, using the self-checkout-machine gate.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';
import {Box3, Vector3, Triangle, Raycaster, DoubleSide} from 'three';
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';
import validator from 'gltf-validator';

const dir = fileURLToPath(new URL('.', import.meta.url));
const spec = JSON.parse(fs.readFileSync(dir + 'backlog.json'));
const bytes = fs.readFileSync(dir + 'exports/optimized.glb');
const doc = JSON.parse(bytes.subarray(20, 20 + bytes.readUInt32LE(12)));
const khronos = await validator.validateBytes(new Uint8Array(bytes), {uri: 'optimized.glb'});
fs.writeFileSync(dir + 'reports/khronos.json', JSON.stringify(khronos, null, 2) + '\n');
assert.equal(khronos.issues.numErrors, 0);
assert.equal(khronos.issues.numWarnings, 0);
assert.ok(doc.buffers.every(b => !b.uri));
assert.ok(!doc.images?.length && !doc.textures?.length && !doc.cameras?.length);
assert.ok(!doc.extensionsUsed?.includes('KHR_lights_punctual'));
assert.ok(!doc.extensionsUsed?.includes('KHR_materials_transmission'), 'no refraction');
assert.equal(doc.materials.length, 2);
const glass = doc.materials.find(m => m.name === 'Glass_PaleAqua_Alpha');
assert.equal(glass.alphaMode, 'BLEND');
assert.ok(glass.pbrMetallicRoughness.baseColorFactor[3] > .1 && glass.pbrMetallicRoughness.baseColorFactor[3] < .4);
assert.equal(doc.scenes[doc.scene].name, 'Closed');
assert.deepEqual(doc.scenes.map(s => s.name), ['Closed', 'Open', 'COLLISION_ONLY_Closed', 'COLLISION_ONLY_Open']);
const load = b => new GLTFLoader().parseAsync(b.buffer.slice(b.byteOffset, b.byteOffset + b.byteLength), '');
const gltf = await load(bytes);
assert.equal(gltf.animations.length, 0);
const near = (a, b, message) => assert.ok(Math.abs(a - b) < 1e-5, `${message}: ${a} / ${b}`);
const variants = [];
let totalTriangles = 0, minArea = Infinity;
for (const [i, variant] of ['Closed', 'Open'].entries()) {
  const scene = gltf.scenes[i];
  scene.updateMatrixWorld(true);
  const root = scene.getObjectByName(spec.root + (i ? '_Open' : ''));
  assert.ok(root);
  assert.equal(scene.children.length, 1);
  assert.deepEqual(root.position.toArray(), [0, 0, 0]);
  assert.equal(root.userData.units, 'metres');
  assert.equal(root.userData.front_axis, 'Blender -Y / glTF +Z');
  assert.equal(root.userData.repeat_pitch_m, 3);
  assert.equal(root.userData.variant, variant);
  const b = new Box3().setFromObject(root, true), dims = b.getSize(new Vector3()).toArray();
  dims.forEach((n, axis) => near(n, spec.dimensions_gltf[axis], 'module dimensions'));
  near(b.min.y, 0, 'floor origin');
  near(b.min.x + b.max.x, 0, 'width centred');
  near(b.min.z + b.max.z, 0, 'depth centred');
  let triangles = 0, primitives = 0;
  const parts = {};
  root.traverse(o => {
    if (!o.isMesh) return;
    const g = o.geometry, p = g.attributes.position, idx = g.index;
    assert.ok(g.attributes.normal);
    assert.ok([...p.array, ...g.attributes.normal.array].every(Number.isFinite));
    const count = idx?.count ?? p.count;
    assert.equal(count % 3, 0);
    triangles += count / 3;
    primitives += g.groups.length || 1;
    const points = Array.from({length: p.count}, (_, j) => new Vector3().fromBufferAttribute(p, j).applyMatrix4(o.matrixWorld));
    for (let j = 0; j < count; j += 3) {
      const area = new Triangle(...[0, 1, 2].map(k => points[idx ? idx.getX(j + k) : j + k])).getArea();
      assert.ok(area > 1e-12, `nondegenerate ${o.name}/${j / 3}`);
      minArea = Math.min(minArea, area);
    }
    parts[o.name] = o.userData.source_parts;
  });
  assert.equal(primitives, 2, 'merged transparent / metal primitives');
  assert.ok(triangles < spec.budget.triangles);
  const sourceNames = Object.values(parts).flat();
  for (const required of ['GLASS_FixedPane_Left', 'GLASS_FixedPane_Right', 'GLASS_OverdoorTransom', 'HEADER_BlankSignBand', 'CHANNEL_Floor_Left', 'CHANNEL_Floor_Right'])
    assert.ok(sourceNames.some(n => n.startsWith(required)), required);
  assert.equal(sourceNames.filter(n => n.startsWith('DOOR_FramelessLeaf')).length, i ? 0 : 2);
  if (!i) {
    assert.equal(sourceNames.filter(n => n.startsWith('PATCH_')).length, 4);
    assert.equal(sourceNames.filter(n => n.startsWith('HANDLE_')).length, 12);
  }
  // Test actual triangles through the aperture, not only declared metadata.
  const ray = new Raycaster();
  let testedRays = 0;
  for (const x of [-.495, -.30, -.1, .1, .30, .495]) for (const y of [.015, .2, 1.3, 2.69, 2.715]) {
    ray.set(new Vector3(x, y, 1), new Vector3(0, 0, -1));
    const hits = ray.intersectObject(root, true);
    if (i) assert.equal(hits.length, 0, `1m clear opening at ${x},${y}`);
    else if (y > .03 && y < 2.7) assert.ok(hits.length, 'closed glass blocks aperture');
    testedRays++;
  }
  for (const x of [-.51, .51]) {
    ray.set(new Vector3(x, 1.3, 1), new Vector3(0, 0, -1));
    assert.ok(ray.intersectObject(root, true).length, 'fixed pane bounds opening');
  }
  ray.set(new Vector3(0, 2.73, 1), new Vector3(0, 0, -1));
  assert.ok(ray.intersectObject(root, true).length, 'transom bounds head clearance');
  let measuredOpening = null;
  if (i) {
    const o = root.getObjectByName('GLASS_FramelessPanes_Open'), p = o.geometry.attributes.position;
    const points = Array.from({length:p.count}, (_, j) => new Vector3().fromBufferAttribute(p,j).applyMatrix4(o.matrixWorld));
    const leftEdge = Math.max(...points.filter(p => p.x < -.49 && p.y < 2.71).map(p => p.x));
    const rightEdge = Math.min(...points.filter(p => p.x > .49 && p.y < 2.71).map(p => p.x));
    const lintel = Math.min(...points.filter(p => Math.abs(p.x) < .501 && p.y > 2.71).map(p => p.y));
    measuredOpening = [rightEdge-leftEdge, lintel];
    near(measuredOpening[0],1,'measured clear width');
    near(measuredOpening[1],2.72,'measured clear height');
  }
  const collisionScene = gltf.scenes[root.userData.collision_scene];
  collisionScene.updateMatrixWorld(true);
  const colliderNode = doc.nodes.find(n => n.name === (i ? 'collider_box_Open' : 'collider_box'));
  assert.equal(colliderNode.extras.hidden, true);
  const cp = doc.meshes[colliderNode.mesh].primitives;
  assert.ok(cp.every(p => p.material === undefined), 'collision mesh has no material');
  const collisionTriangles = cp.reduce((sum, p) => sum + doc.accessors[p.indices].count / 3, 0);
  assert.equal(collisionTriangles, i ? 36 : 12);
  assert.equal(root.getObjectByName(colliderNode.name), undefined, 'collider hidden from visual scene');
  collisionScene.traverse(o => {if (o.isMesh) o.material.side = DoubleSide;});
  for (const x of [-.49, 0, .49]) {
    ray.set(new Vector3(x, 1.3, 1), new Vector3(0, 0, -1));
    assert.equal(Boolean(ray.intersectObject(collisionScene, true).length), !i, 'collider respects open passage');
  }
  // Repeated modules meet exactly at +/-1.5 without a duplicated jamb.
  near(b.max.x, b.min.x + spec.repeat_pitch_m, 'tile seam');
  totalTriangles += triangles + collisionTriangles;
  variants.push({name: variant, dimensions_metres_gltf: dims, bounds: {min: b.min.toArray(), max: b.max.toArray()},
    visible_triangles: triangles, collider_triangles: collisionTriangles, visible_primitives: primitives,
    aperture_rays: testedRays, clear_opening_metres:measuredOpening, source_parts: parts});
}
assert.ok(totalTriangles < spec.budget.triangles, 'entire delivery including variants and colliders');
assert.ok(bytes.length < spec.budget.bytes);
let sourceEdit = 'NOT RUN';
if (process.argv.includes('--source-edit')) {
  const edited = await load(fs.readFileSync('/tmp/glass-storefront-module-source-edit.glb'));
  edited.scene.updateMatrixWorld(true);
  const original = new Box3().setFromObject(gltf.scene.getObjectByName('METAL_HeaderChannelFittings_Closed'), true);
  const changed = new Box3().setFromObject(edited.scene.getObjectByName('METAL_HeaderChannelFittings_Closed'), true);
  near(changed.max.y - original.max.y, .02, 'saved header edit survives export');
  const untouched = new Box3().setFromObject(edited.scenes[1], true);
  near(untouched.max.y, 3.6, 'Open variant unchanged');
  sourceEdit = 'PASS: reopened source; Closed header raised 20 mm in temporary export; Open unchanged';
}
const report = {result: 'PASS', id: spec.slug, glb_bytes: bytes.length, triangles: totalTriangles,
  materials: doc.materials.length, textures: 0, animations: 0, min_triangle_area_m2: minArea,
  sha256: createHash('sha256').update(bytes).digest('hex'),
  validation: {errors: 0, warnings: 0}, variants, source_edit: sourceEdit, budget: spec.budget};
fs.writeFileSync(dir + 'reports/assets.json', JSON.stringify(report, null, 2) + '\n');
console.log(JSON.stringify(report, null, 2));

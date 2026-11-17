// Independently load and measure the delivered GLB, following self-checkout-machine.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';
import {Box3, Vector3, Triangle, Raycaster} from 'three';
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
assert.ok(doc.materials.length <= spec.budget.materials);
const load = b => new GLTFLoader().parseAsync(b.buffer.slice(b.byteOffset, b.byteOffset + b.byteLength), '');
const gltf = await load(bytes);
gltf.scene.updateMatrixWorld(true);
const root = gltf.scene.getObjectByName(spec.root);
assert.ok(root);
assert.deepEqual(root.position.toArray(), [0, 0, 0]);
assert.equal(root.userData.units, 'metres');
assert.equal(root.userData.front_axis, 'Blender -Y / glTF +Z');
assert.equal(gltf.animations.length, 0);
assert.equal(gltf.scene.children.length, 1);
const bounds = new Box3().setFromObject(root, true);
const dimensions = bounds.getSize(new Vector3()).toArray();
for (const [axis, expected] of spec.dimensions_gltf.entries())
  assert.ok(Math.abs(dimensions[axis] - expected) < .012, `metre envelope ${axis}: ${dimensions[axis]}`);
assert.ok(Math.abs(bounds.min.y) < 1e-6, 'wheels touch floor');
assert.ok(Math.abs(bounds.min.x + bounds.max.x) < .006 && Math.abs(bounds.min.z + bounds.max.z) < .006, 'floor-centred footprint');

let visibleTriangles = 0, vertices = 0, minArea = Infinity, visualPrimitives = 0;
const parts = {}, palette = new Set();
root.traverse(o => {
  if (!o.isMesh) return;
  const g = o.geometry, p = g.attributes.position, idx = g.index;
  assert.ok(g.attributes.normal && g.attributes.color, 'normals and original vertex colours');
  assert.ok([...p.array, ...g.attributes.normal.array, ...g.attributes.color.array].every(Number.isFinite));
  const count = idx?.count ?? p.count;
  assert.equal(count % 3, 0);
  visibleTriangles += count / 3;
  visualPrimitives++;
  vertices += p.count;
  const points = Array.from({length: p.count}, (_, i) => new Vector3().fromBufferAttribute(p, i).applyMatrix4(o.matrixWorld));
  for (let i = 0; i < count; i += 3) {
    const area = new Triangle(...[0, 1, 2].map(j => points[idx ? idx.getX(i + j) : i + j])).getArea();
    assert.ok(area > 1e-12, `nondegenerate ${o.name}/${i / 3}`);
    minArea = Math.min(minArea, area);
  }
  for (let i = 0; i < g.attributes.color.count; i++)
    palette.add([g.attributes.color.getX(i), g.attributes.color.getY(i), g.attributes.color.getZ(i)].map(v => v.toFixed(3)).join(','));
});
for (const name of spec.features) {
  const o = root.getObjectByName(name);
  assert.ok(o, 'required independent node ' + name);
  const b = new Box3().setFromObject(o, true);
  parts[name] = {min: b.min.toArray(), max: b.max.toArray(), source_parts: o.userData.source_parts};
}
assert.ok(palette.size >= 8);
assert.ok(visualPrimitives <= spec.budget.visible_primitives);
const tubs = root.getObjectByName('FLAVOUR_ThreeTubs');
assert.equal(tubs.userData.flavour_count, 3);
assert.equal(tubs.userData.inspect_target, true);
assert.ok(tubs.isMesh, 'tubs use one focused mesh');
// Independently verify three real geometric tub groups across the counter.
const pos = tubs.geometry.attributes.position;
const flavourColours = [[.87, .54, .60], [1, .86, .55], [.38, .64, .51]];
const colourBounds = (mesh, rgb) => {
  const linear = rgb.map(v => v <= .04045 ? v / 12.92 : ((v + .055) / 1.055) ** 2.4);
  const {position, color} = mesh.geometry.attributes;
  const points = [];
  for (let i = 0; i < position.count; i++) {
    if ([color.getX(i), color.getY(i), color.getZ(i)].every((v, j) => Math.abs(v - linear[j]) < 1e-5))
      points.push(new Vector3().fromBufferAttribute(position, i).applyMatrix4(mesh.matrixWorld));
  }
  assert.ok(points.length, 'authored flavour colour has geometry');
  return new Box3().setFromPoints(points);
};
const clusters = [-.325, 0, .325].map(x => {
  const points = Array.from({length: pos.count}, (_, i) => new Vector3().fromBufferAttribute(pos, i).applyMatrix4(tubs.matrixWorld))
    .filter(p => Math.abs(p.x - x) < .15);
  const b = new Box3().setFromPoints(points);
  assert.ok(points.length > 50 && b.getSize(new Vector3()).x > .28);
  assert.ok(b.getSize(new Vector3()).y >= .117 && b.min.y > .99 && b.min.z > .006,
    'deep flavour containers above counter and facing +Z');
  return {min: b.min.toArray(), max: b.max.toArray()};
});
const ray = new Raycaster();
const tubRecesses = flavourColours.map((rgb, i) => {
  const food = colourBounds(tubs, rgb);
  ray.set(new Vector3([-.325, 0, .325][i], 1.3, .128), new Vector3(0, -1, 0));
  const hit = ray.intersectObject(tubs)[0];
  assert.ok(hit && Math.abs(hit.point.y - food.max.y) < 1e-6, 'tub opening exposes the frozen surface');
  const recess = clusters[i].max[1] - food.max.y;
  assert.ok(recess >= .039 && recess <= .041, 'food is recessed 40 mm below the rim');
  return {food_min: food.min.toArray(), food_max: food.max.toArray(), recess_metres: recess};
});
const tray = root.getObjectByName('TRAY_BarsAndWafers');
const trayContacts = flavourColours.map((rgb, i) => {
  const bar = colourBounds(tray, rgb);
  const size = bar.getSize(new Vector3());
  assert.ok(size.x / size.z > 2 && size.y > .03, 'elongated rounded ice bar');
  ray.set(new Vector3([-.29, -.145, 0][i], 1.2, .38), new Vector3(0, -1, 0));
  const support = ray.intersectObject(tray)[0];
  assert.ok(support, 'tray liner below ice bar');
  const gap = bar.min.y - support.point.y;
  assert.ok(Math.abs(gap) < 1e-6, 'exported ice bar touches liner without floating or penetration');
  assert.ok(parts.TRAY_BarsAndWafers.source_parts.includes(`STICK_0${i + 1}_PlainWoodGrip`));
  return {bar_min: bar.min.toArray(), bar_max: bar.max.toArray(), liner_top: support.point.y, gap_metres: gap};
});
assert.ok(parts.SERVICE_Flap.max[2] > .33, 'service flap on +Z front');
assert.ok(parts.TRAY_BarsAndWafers.max[2] > .39, 'tray on +Z front');

const colliderIndex = doc.nodes.findIndex(n => n.name === 'collider_box');
const collider = doc.nodes[colliderIndex];
assert.ok(collider && collider.mesh !== undefined);
assert.equal(collider.extras.hidden, true);
assert.equal(root.getObjectByName('collider_box'), undefined, 'hidden from default visual scene');
assert.deepEqual(doc.scenes[root.userData.collision_scene].nodes, [colliderIndex]);
const collisionPrimitives = doc.meshes[collider.mesh].primitives;
assert.ok(collisionPrimitives.every(p => p.material === undefined), 'collider has no material');
const colliderTriangles = collisionPrimitives.reduce((sum, p) => sum + doc.accessors[p.indices].count / 3, 0);
assert.equal(colliderTriangles, 12);
gltf.scenes[root.userData.collision_scene].updateMatrixWorld(true);
const cb = new Box3().setFromObject(gltf.scenes[root.userData.collision_scene], true);
assert.ok(Math.abs(cb.min.y) < 1e-6 && cb.max.y > 1.05);
assert.ok(cb.min.x < -.648 && cb.max.x > .648 && cb.min.z < -.39 && cb.max.z > .39);
assert.ok(visibleTriangles + colliderTriangles <= spec.budget.triangles);
assert.ok(bytes.length < spec.budget.bytes);

let sourceEdit = 'NOT RUN';
if (process.argv.includes('--source-edit')) {
  const edited = await load(fs.readFileSync('/tmp/ice-cream-cart-potong-source-edit.glb'));
  edited.scene.updateMatrixWorld(true);
  const moved = new Box3().setFromObject(edited.scene.getObjectByName('FLAVOUR_ThreeTubs'), true);
  const original = new Box3().setFromObject(tubs, true);
  for (const edge of ['min', 'max']) assert.ok(Math.abs(moved[edge].y - original[edge].y - .02) < 1e-6);
  const unchanged = new Box3().setFromObject(edited.scene.getObjectByName('UMBRELLA_Canopy'), true);
  for (const edge of ['min', 'max']) assert.ok(Math.abs(unchanged[edge].y - parts.UMBRELLA_Canopy[edge][1]) < 1e-6);
  sourceEdit = 'PASS: reopened saved source edit, exported tubs 20 mm higher, umbrella unchanged';
}
const report = {result: 'PASS', id: spec.slug, triangles: visibleTriangles + colliderTriangles,
  visible_triangles: visibleTriangles, collider_triangles: colliderTriangles, vertices,
  glb_bytes: bytes.length, visible_mesh_nodes: spec.features.length, visible_primitives: visualPrimitives,
  materials: doc.materials.length, textures: 0, animations: 0, dimensions_metres_gltf: dimensions,
  bounds: {min: bounds.min.toArray(), max: bounds.max.toArray()}, palette_colors: palette.size,
  tub_bounds: clusters, tub_recesses: tubRecesses, tray_contacts: trayContacts, min_triangle_area_m2: minArea,
  collider: {default_scene_visible: false, material: null, min: cb.min.toArray(), max: cb.max.toArray()},
  sha256: createHash('sha256').update(bytes).digest('hex'),
  validation: {errors: khronos.issues.numErrors, warnings: khronos.issues.numWarnings},
  budget: spec.budget, source_edit: sourceEdit, parts};
fs.writeFileSync(dir + 'reports/assets.json', JSON.stringify(report, null, 2) + '\n');
console.log(JSON.stringify(report, null, 2));

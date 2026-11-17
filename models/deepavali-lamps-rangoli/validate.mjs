import assert from 'node:assert/strict';
import fs from 'node:fs';
import { fileURLToPath } from 'node:url';
import { createHash } from 'node:crypto';
import { Box3, Vector3 } from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import validator from 'gltf-validator';

const dir = fileURLToPath(new URL('.', import.meta.url));
const spec = JSON.parse(fs.readFileSync(dir + 'backlog.json'));
const bytes = fs.readFileSync(process.argv[2] ?? dir + 'exports/optimized.glb');
const json = JSON.parse(bytes.subarray(20, 20 + bytes.readUInt32LE(12)));
const validation = await validator.validateBytes(new Uint8Array(bytes), { uri: 'optimized.glb', maxIssues: 200 });
assert.equal(validation.issues.numErrors, 0);
assert.equal(validation.issues.numWarnings, 0);
assert.ok(!json.images?.length && !json.textures?.length && !json.cameras?.length && !json.extensions?.KHR_lights_punctual);
assert.ok(json.buffers.every(b => !b.uri));
assert.equal(json.materials.length, 3);
assert.ok(json.materials.every(m => !m.alphaMode || m.alphaMode === 'OPAQUE'));
const gltf = await new GLTFLoader().parseAsync(bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength), '');
gltf.scene.updateMatrixWorld(true);
const root = gltf.scene.getObjectByName(spec.root);
assert.ok(root);
assert.deepEqual(root.position.toArray(), [0, 0, 0]);
assert.equal(root.userData.units, 'metres');
assert.equal(root.userData.front_axis, 'Blender -Y / glTF +Z');
assert.equal(gltf.animations.length, 0);
const bounds = new Box3().setFromObject(root, true);
const dimensions = bounds.getSize(new Vector3()).toArray();
assert.ok(Math.abs(bounds.min.y) < 1e-6);
assert.ok(Math.abs(dimensions[0] - 2.4) < 1e-5 && Math.abs(dimensions[2] - 2.4) < 1e-5);
assert.ok(Math.abs(bounds.getCenter(new Vector3()).x) < 1e-6 && Math.abs(bounds.getCenter(new Vector3()).z) < 1e-6);

let triangles = 0, vertices = 0, primitives = 0, degenerates = 0;
const components = {};
const floorPoints = [new Set(), new Set(), new Set()];
const key = v => v.toArray().map(n => Math.round(n * 1e6)).join(',');
const floorBounds = new Box3();
const floorSolidBounds = new Box3();
root.traverse(o => {
  if (!o.isMesh) return;
  const p = o.geometry.attributes.position, n = o.geometry.attributes.normal, ix = o.geometry.index;
  assert.ok(n && [...p.array, ...n.array].every(Number.isFinite));
  assert.equal(o.geometry.groups.length, 0, 'one material per delivery mesh');
  const mi = ['Terracotta', 'MarigoldGold', 'RiceIvory'].indexOf(o.material.name);
  assert.ok(mi >= 0);
  const count = ix?.count ?? p.count;
  triangles += count/3;
  vertices += p.count;
  primitives++;
  const points = [], ids = [], unique = new Map(), parents = [];
  for (let i = 0; i < p.count; i++) {
    const v = new Vector3().fromBufferAttribute(p, i).applyMatrix4(o.matrixWorld);
    assert.ok(Math.abs(new Vector3().fromBufferAttribute(n, i).length() - 1) < 1e-4);
    const k = key(v);
    if (!unique.has(k)) { unique.set(k, points.length); parents.push(points.length); points.push(v); }
    ids.push(unique.get(k));
    if (Math.abs(v.y - .008) < 1e-6) {
      floorPoints[mi].add(key(new Vector3(v.x, .008, v.z)));
      floorBounds.expandByPoint(v);
    }
    if (v.y <= .008 + 1e-6) {
      assert.ok(Math.hypot(v.x, v.z) <= 1.2 + 1e-6, 'circular floor');
      floorSolidBounds.expandByPoint(v);
    }
  }
  function find(i) { while (parents[i] !== i) { parents[i] = parents[parents[i]]; i = parents[i]; } return i; }
  function union(a, b) { parents[find(a)] = find(b); }
  const at = i => ix ? ix.getX(i) : i;
  for (let i = 0; i < count; i += 3) {
    const a = ids[at(i)], b = ids[at(i+1)], c = ids[at(i+2)];
    union(a, b); union(b, c);
    const cross = points[b].clone().sub(points[a]).cross(points[c].clone().sub(points[a]));
    if (cross.lengthSq() < 1e-20) degenerates++;
  }
  const boxes = new Map();
  for (let i = 0; i < points.length; i++) {
    const component = find(i);
    if (!boxes.has(component)) boxes.set(component, new Box3());
    boxes.get(component).expandByPoint(points[i]);
  }
  components[o.material.name] = [...boxes.values()];
});
assert.equal(degenerates, 0);
assert.equal(primitives, spec.budget.mesh_primitives);
assert.ok(triangles <= spec.budget.triangles && bytes.length < spec.budget.bytes);

// Independently recover actual connected geometry, rather than accepting names,
// feature extras or metadata as evidence of twelve lamps and fifty flowers.
const height = b => b.getSize(new Vector3()).y;
const bowls = components.Terracotta.filter(b => b.min.y >= .008-1e-6 && b.max.y < .08 && height(b) > .06);
const flames = components.MarigoldGold.filter(b => b.min.y > .077 && b.max.y < .15 && height(b) > .06);
const flowers = components.MarigoldGold.filter(b => b.min.y > 1.2 && height(b) > .08);
assert.equal(bowls.length, 12);
assert.equal(flames.length, 12);
assert.equal(flowers.length, 50);
const lampBounds = new Box3();
for (const bowl of bowls) {
  lampBounds.union(bowl);
  const centre = bowl.getCenter(new Vector3());
  const nearest = flames.filter(b => b.getCenter(new Vector3()).distanceTo(centre) < .18);
  assert.equal(nearest.length, 1, 'one real flame per clay bowl');
  lampBounds.union(nearest[0]);
}
const lampDimensions = lampBounds.getSize(new Vector3()).toArray();
assert.ok(lampDimensions[0] <= 2 && lampDimensions[2] <= 2, 'all lamps in the two metre square');
assert.ok(lampBounds.min.x >= -1 && lampBounds.max.x <= 1 && lampBounds.min.z >= -1 && lampBounds.max.z <= 1);
const garlandBounds = [];
for (const sign of [-1, 1]) {
  const group = flowers.filter(b => Math.sign(b.getCenter(new Vector3()).x) === sign);
  assert.equal(group.length, 25, 'two distinct flower strings');
  const box = new Box3();
  group.forEach(b => box.union(b));
  garlandBounds.push({ min: box.min.toArray(), max: box.max.toArray(), flowers: group.length });
}
// Twelve-fold symmetry is checked on actual exported top-surface coordinates
// for every plain colour, including the 24 repeated border marks.
for (const set of floorPoints) {
  assert.ok(set.size > 100);
  for (const item of set) {
    const [x, , z] = item.split(',').map(Number).map(n => n/1e6);
    const a = Math.PI/6;
    const target = [x*Math.cos(a)-z*Math.sin(a), .008, x*Math.sin(a)+z*Math.cos(a)];
    assert.ok([...set].some(k => k.split(',').map(Number).every((v, i) => Math.abs(v/1e6-target[i]) < 2e-6)), 'twelve-fold colour symmetry');
  }
}
const report = {
  result: 'PASS', id: spec.slug, glb_bytes: bytes.length, triangles, vertices, primitives,
  materials: json.materials.length, animations: gltf.animations.length, degenerate_triangles: degenerates,
  dimensions, dimension_order: 'X width, Y height, Z depth',
  bounds: { min: bounds.min.toArray(), max: bounds.max.toArray() },
  sha256: createHash('sha256').update(bytes).digest('hex'),
  validation: { errors: validation.issues.numErrors, warnings: validation.issues.numWarnings, validator: validation.validatorVersion },
  features: { clay_diyas: bowls.length, flame_meshes: flames.length, hanging_garlands: garlandBounds.length,
    marigold_heads: flowers.length, lamp_group_dimensions: lampDimensions,
    lamp_group_bounds: { min: lampBounds.min.toArray(), max: lampBounds.max.toArray() },
    rangoli_diameter: floorBounds.getSize(new Vector3()).x, rangoli_thickness: floorSolidBounds.getSize(new Vector3()).y,
    rangoli_colours: floorPoints.length, rotational_symmetry_order: 12, garlands: garlandBounds },
  limits: 'Static flame meshes; no light emission, fire simulation, rigging certification, mobile or full-mall performance verification.'
};
if (!process.argv[2]) {
  fs.writeFileSync(dir+'reports/khronos.json', JSON.stringify(validation, null, 2)+'\n');
  fs.writeFileSync(dir+'reports/assets.json', JSON.stringify(report, null, 2)+'\n');
}
console.log(JSON.stringify(report, null, 2));

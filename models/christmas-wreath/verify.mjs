import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { readFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import validator from 'gltf-validator';
import { Box3, Raycaster, Vector3 } from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';

const file = process.argv[2] ?? fileURLToPath(new URL('./exports/christmas-wreath.glb', import.meta.url));
const bytes = await readFile(file);
const glb = JSON.parse(bytes.subarray(20, 20 + bytes.readUInt32LE(12)).toString());
const { issues } = await validator.validateBytes(bytes);
assert.equal(issues.numErrors, 0);
assert.equal(issues.numWarnings, 0);
assert.equal(glb.buffers.length, 1);
assert.equal(glb.buffers[0].uri, undefined);
for (const kind of ['images', 'textures', 'animations', 'cameras', 'skins']) {
  assert.equal((glb[kind] ?? []).length, 0, kind);
}
assert.deepEqual(glb.scenes[0].nodes.map(i => glb.nodes[i].name), ['ASSET_ChristmasWreath']);
const geometry = glb.meshes.flatMap(mesh => mesh.primitives);
const triangles = geometry.reduce((sum, part) => sum + glb.accessors[part.indices].count / 3, 0);
const vertices = geometry.reduce((sum, part) => sum + glb.accessors[part.attributes.POSITION].count, 0);
assert.ok(triangles < 100_000 && bytes.length < 5 * 1_048_576);
assert.ok(glb.nodes.every(node => !/Studio|window|fill|camera/i.test(node.name)));
const foliage = geometry.filter(part => glb.materials[part.material].name === 'Evergreen needle bloom');
assert.ok(foliage.length && foliage.every(part => part.attributes.COLOR_0 !== undefined));
assert.equal(glb.materials[foliage[0].material].doubleSided, true);

const { scene } = await new GLTFLoader().parseAsync(bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength), '');
scene.updateMatrixWorld(true);
const bounds = new Box3().setFromObject(scene, true);
const ray = new Raycaster();
function cast(object, origin, direction) {
  ray.set(new Vector3(...origin), new Vector3(...direction));
  return ray.intersectObject(object, true);
}
let clearProbes = 0;
for (let ix = -5; ix <= 5; ix++) {
  for (let iy = -5; iy <= 5; iy++) {
    if (ix * ix + iy * iy > 25) continue;
    assert.equal(cast(scene, [ix * .015, iy * .015, .40], [0, 0, -1]).length, 0);
    clearProbes++;
  }
}
for (let i = 0; i < 16; i++) {
  const angle = 2 * Math.PI * i / 16;
  assert.ok(cast(scene, [.174 * Math.cos(angle), .174 * Math.sin(angle), .40], [0, 0, -1]).length);
}
const hanger = scene.getObjectByName('Rear_keyhole_and_twin_wire_lashings');
assert.ok(hanger);
const aperture = [0, .207, .0055];
const distances = [-1, 1].map(dir => cast(hanger, aperture, [dir, 0, 0])[0].distance);
const width = distances[0] + distances[1];
assert.ok(width > .014 && width < .025);
assert.equal(cast(hanger, [0, .207, -.02], [0, 0, 1]).length, 0);
const rearClearance = cast(scene, aperture, [0, 0, 1])[0]?.distance;
assert.ok(rearClearance > .009);
const round = number => Number(number.toFixed(7));
const xyz = vec => vec.toArray().map(round);
console.log(JSON.stringify({
  sha256: createHash('sha256').update(bytes).digest('hex'),
  bytes: bytes.length, triangles, vertices, meshes: glb.meshes.length,
  primitives: geometry.length, materials: glb.materials.length,
  bounds_m: {min: xyz(bounds.min), max: xyz(bounds.max), dimensions: xyz(bounds.getSize(new Vector3()))},
  centre_disk: {diameter_m: .15, clear_rays: clearProbes, ring_positive_controls: 16},
  hanger: {height_probed_m: .207, internal_width_m: round(width), depth_to_foliage_m: round(rearClearance)},
  khronos: {errors: issues.numErrors, warnings: issues.numWarnings, infos: issues.numInfos, hints: issues.numHints},
}, null, 2));

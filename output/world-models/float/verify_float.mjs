import assert from 'node:assert/strict';
import { readFile, writeFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { Box3 } from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { validateBytes } from 'gltf-validator';

const file = 'float.glb';
const data = await readFile(new URL(file, import.meta.url));
const validation = await validateBytes(new Uint8Array(data), { uri: file });
const { numErrors, numWarnings, numInfos, numHints, messages } = validation.issues;
assert.equal(numErrors + numWarnings, 0, JSON.stringify(messages));
assert.equal(data.toString('ascii', 0, 4), 'glTF');

const jsonLength = data.readUInt32LE(12);
const json = JSON.parse(data.toString('utf8', 20, 20 + jsonLength));
for (const field of ['images', 'textures', 'cameras', 'animations', 'skins', 'extensionsRequired']) {
  assert.equal(json[field]?.length ?? 0, 0, field);
}
assert.equal(json.extensions?.KHR_lights_punctual, undefined);
assert.equal(json.buffers.length, 1);
assert.equal(json.buffers[0].uri, undefined);
assert.ok(data.byteLength <= 1.8 * 1024 * 1024, 'File budget exceeded');

const buffer = data.buffer.slice(data.byteOffset, data.byteOffset + data.byteLength);
const { scene } = await new GLTFLoader().parseAsync(buffer, '');
scene.updateMatrixWorld(true);

const expected = [
  'Platform_Deck', 'Steel_Pontoon_Array', 'Edge_Fascia_and_Fenders',
  'Detachable_Mooring_Pylons', 'Perimeter_Guardrails', 'Performance_Riser_and_Stairs',
  'Main_Stage_Proscenium', 'Stage_Tower_Left', 'Stage_Tower_Right',
  'Overhead_Lighting_Trusses', 'Lighting_Fixtures', 'LED_Screen_Main',
  'LED_Screens_Wings', 'Stage_Wing_Cladding',
];
assert.deepEqual(scene.children.map(part => part.name).sort(), expected.sort());
const rounded = value => Number(value.toFixed(3));
const dimensions = box => box.max.clone().sub(box.min).toArray().map(rounded);
const near = (actual, target) => assert.ok(Math.abs(actual - target) < 0.002,
  `Expected ${target}, got ${actual}`);

const materials = json.materials.map(item => item.name).sort();
const approved = new Set(
  'paint glass window wall roof concrete metal chrome trim stone water leaf trunk light lamp_emissive rubber plate'.split(' '),
);
assert.ok(materials.every(name => approved.has(name)), 'Unexpected material name');

let triangles = 0;
const parts = scene.children.map(part => {
  let count = 0;
  part.traverse(obj => {
    if (obj.isMesh) count += (obj.geometry.index?.count ?? obj.geometry.attributes.position.count) / 3;
  });
  assert.ok(Number.isInteger(count) && count > 0, part.name);
  triangles += count;
  return { name: part.name, triangles: count };
});
assert.ok(triangles <= 8000, `Triangle budget exceeded at ${triangles}`);

const bounds = name => new Box3().setFromObject(scene.getObjectByName(name), true);
const model = new Box3().setFromObject(scene, true);
const deck = bounds('Platform_Deck');
const screen = bounds('LED_Screen_Main');
const rig = bounds('Overhead_Lighting_Trusses');
near(dimensions(model)[0], 85);
near(dimensions(model)[2], 125);
near(dimensions(deck)[0], 83);
near(dimensions(deck)[2], 120);
near(deck.min.x + deck.max.x, 0);
near(deck.min.z + deck.max.z, 0);
near(deck.max.y, 1.207);
near(bounds('Main_Stage_Proscenium').max.y, 31.2);
near(bounds('Stage_Tower_Left').max.y, 26.2);
near(bounds('Stage_Tower_Right').max.y, 26.2);
near(dimensions(screen)[0], 60);
near(dimensions(screen)[1], 15);
// Screen sits at the -Z short end, with display material on its high-Z face.
assert.ok(screen.max.z < -40 && rig.max.z > screen.max.z);
const screenNormals = [];
scene.getObjectByName('LED_Screen_Main').traverse(obj => {
  if (!obj.isMesh || obj.material.name !== 'glass') return;
  const positions = obj.geometry.attributes.position;
  const normals = obj.geometry.attributes.normal;
  for (let i = 0; i < positions.count; i++) {
    if (normals.getZ(i) > 0.99) screenNormals.push(positions.getZ(i));
  }
});
assert.ok(screenNormals.length > 0 && screenNormals.every(z => z > -43.4));

const metadata = {
  file,
  triangles,
  bytes: data.byteLength,
  sha256: createHash('sha256').update(data).digest('hex'),
  size_metres: { width_x: dimensions(model)[0], height_y: dimensions(model)[1], length_z: dimensions(model)[2] },
  bounds_metres: { min_xyz: model.min.toArray().map(rounded), max_xyz: model.max.toArray().map(rounded) },
  origin: 'Center of the deck plan at water level',
  up_axis: '+Y',
  front_axis: '+Z',
  materials,
  parts,
  validator: { version: validation.validatorVersion, errors: numErrors, warnings: numWarnings, infos: numInfos, hints: numHints },
};
await writeFile(new URL('models.json', import.meta.url), JSON.stringify([metadata], null, 2) + '\n');
console.log(JSON.stringify(metadata, null, 2));

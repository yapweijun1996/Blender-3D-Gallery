import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { readFile, readdir, stat, writeFile } from 'node:fs/promises';
import validator from 'gltf-validator';

const root = new URL('./', import.meta.url);
const specs = {
  road_light: 700, gantry_sign: 900, direction_sign: 300, speed_sign: 200,
  keep_left: 150, ped_signal: 450, mast_signal: 900, bus_shelter_sbs: 1400,
  bus_stop_flag: 300, kerb_drain: 350, drain_grate: 100, manhole: 60,
  guard_rail_3m: 300, bollard: 100, bins: 500, hydrant: 200,
  covered_walkway: 900, kiosk_substation: 500, tactile_strip: 120, road_markings: 800,
};
const palette = new Set([
  'paint', 'glass', 'window', 'wall', 'roof', 'concrete', 'metal', 'chrome',
  'trim', 'stone', 'water', 'leaf', 'trunk', 'light', 'lamp_emissive', 'rubber', 'plate',
]);
const markingParts = ['zebra', 'yellow_box', 'bus_lane', 'stop_line',
  'arrow_straight', 'arrow_left', 'arrow_right'];
const maxBytes = Math.floor(1.8 * 1024 ** 2);
const close = (actual, expected) => assert.ok(Math.abs(actual - expected) < 0.0001, `${actual} != ${expected}`);
const sha256 = bytes => createHash('sha256').update(bytes).digest('hex');
const metres = values => values.map(value => Math.round(value * 10000) / 10000);

function readGlb(bytes) {
  assert.equal(bytes.toString('ascii', 0, 4), 'glTF');
  assert.equal(bytes.readUInt32LE(4), 2);
  assert.equal(bytes.readUInt32LE(8), bytes.length);
  const jsonLength = bytes.readUInt32LE(12);
  assert.equal(bytes.toString('ascii', 16, 20), 'JSON');
  const jsonEnd = 20 + jsonLength;
  assert.equal(bytes.toString('ascii', jsonEnd + 4, jsonEnd + 8), 'BIN\0');
  return [JSON.parse(bytes.toString('utf8', 20, jsonEnd)), bytes.subarray(jsonEnd + 8)];
}

const component = {
  5121: [1, 'readUInt8'],
  5123: [2, 'readUInt16LE'],
  5125: [4, 'readUInt32LE'],
  5126: [4, 'readFloatLE'],
};

function accessor(document, binary, index, size) {
  const spec = document.accessors[index];
  const view = document.bufferViews[spec.bufferView];
  const [bytes, method] = component[spec.componentType];
  const origin = (view.byteOffset ?? 0) + (spec.byteOffset ?? 0);
  const stride = view.byteStride ?? bytes * size;
  return (i, axis = 0) => binary[method](origin + stride * i + bytes * axis);
}

function geometry(document, binary) {
  const min = [Infinity, Infinity, Infinity];
  const max = [-Infinity, -Infinity, -Infinity];
  let triangles = 0;
  const parts = [];
  for (const id of document.scenes[document.scene ?? 0].nodes) {
    const node = document.nodes[id];
    const offset = node.translation ?? [0, 0, 0];
    assert.ok(node.name && !node.rotation && !node.scale && !node.matrix && !node.children);
    parts.push(node.name);
    for (const primitive of document.meshes[node.mesh].primitives) {
      const position = document.accessors[primitive.attributes.POSITION];
      const indexes = document.accessors[primitive.indices];
      assert.equal(primitive.mode ?? 4, 4);
      assert.ok(primitive.attributes.COLOR_0 !== undefined && primitive.attributes.NORMAL !== undefined);
      assert.equal(indexes.count % 3, 0);
      triangles += indexes.count / 3;
      for (let j = 0; j < 3; j += 1) {
        min[j] = Math.min(min[j], position.min[j] + offset[j]);
        max[j] = Math.max(max[j], position.max[j] + offset[j]);
      }
      const point = accessor(document, binary, primitive.attributes.POSITION, 3);
      const index = accessor(document, binary, primitive.indices, 1);
      for (let i = 0; i < indexes.count; i += 3) {
        const [a, b, c] = [index(i), index(i + 1), index(i + 2)];
        const u = [0, 1, 2].map(axis => point(b, axis) - point(a, axis));
        const v = [0, 1, 2].map(axis => point(c, axis) - point(a, axis));
        const areaVector = [
          u[1] * v[2] - u[2] * v[1],
          u[2] * v[0] - u[0] * v[2],
          u[0] * v[1] - u[1] * v[0],
        ];
        assert.ok(Math.hypot(...areaVector) > 1e-13, `Degenerate triangle in ${node.name}`);
      }
    }
  }
  assert.equal(new Set(parts).size, parts.length);
  assert.equal(document.meshes.length, parts.length);
  assert.equal(document.nodes.length, parts.length);
  return { triangles, min, max, parts };
}

function checkDimensions(name, min, max, parts, document, binary) {
  close(min[1], 0);
  assert.ok(min[0] < 0 && max[0] > 0 && min[2] < 0 && max[2] > 0);
  const width = max[0] - min[0];
  if (name === 'covered_walkway') close(width, 6);
  if (name === 'kerb_drain' || name === 'tactile_strip') close(width, 4);
  if (name === 'guard_rail_3m') close(width, 3);
  if (name === 'road_light') {
    const pole = document.nodes.find(node => node.name === 'tapered_pole_and_arm');
    const top = Math.max(...document.meshes[pole.mesh].primitives.map(
      primitive => document.accessors[primitive.attributes.POSITION].max[1]));
    close(top, 10);
  }
  if (name === 'gantry_sign') {
    const location = n => document.nodes.find(node => node.name === n).translation[0];
    close(location('right_support') - location('left_support'), 16);
    const node = document.nodes.find(node => node.name === 'green_direction_panel');
    const panel = document.meshes[node.mesh].primitives;
    close(Math.min(...panel.map(p => document.accessors[p.attributes.POSITION].min[1])) + node.translation[1], 5.7);
  }
  if (name === 'road_markings') {
    close(max[1], 0);
    assert.deepEqual(parts, markingParts);
    const bounds = [];
    for (const [name, direction] of [['arrow_left', 1], ['arrow_right', -1]]) {
      const node = document.nodes.find(node => node.name === name);
      const { POSITION } = document.meshes[node.mesh].primitives[0].attributes;
      const { min, max, count } = document.accessors[POSITION];
      const point = accessor(document, binary, POSITION, 3);
      const tail = Array.from({ length: count }, (_, i) => i)
        .filter(i => Math.abs(point(i, 2) - min[2]) < 0.0001)
        .map(i => point(i));
      const tailCenter = (Math.min(...tail) + Math.max(...tail)) / 2;
      assert.ok(direction > 0 ? max[0] - tailCenter > 1 : tailCenter - min[0] > 1,
        `${name} points to the wrong side of +Z travel`);
      bounds.push([min[0] + node.translation[0], max[0] + node.translation[0]]);
    }
    assert.ok(bounds[0][0] > bounds[1][1], 'Overlapping turn-arrow layout');
  }
}

const expected = Object.keys(specs).map(name => `${name}.glb`).sort();
assert.deepEqual((await readdir(root)).filter(file => file.endsWith('.glb')).sort(), expected);
const models = [];
let failures = 0;

for (const [name, budget] of Object.entries(specs)) {
  const file = `${name}.glb`;
  try {
    const url = new URL(file, root);
    const bytes = await readFile(url);
    const [document, binary] = readGlb(bytes);
    assert.match(document.asset.generator, /^Khronos glTF Blender I\/O v/);
    assert.ok(document.buffers.length === 1 && !document.buffers[0].uri);
    for (const key of ['animations', 'cameras', 'skins', 'images', 'textures']) {
      assert.ok(!document[key]?.length, `Unexpected ${key}`);
    }
    assert.ok(!document.extensionsUsed?.includes('KHR_lights_punctual'));
    const report = await validator.validateBytes(new Uint8Array(bytes), { uri: file });
    const { numErrors: errors, numWarnings: warnings, messages } = report.issues;
    assert.ok(!errors && !warnings, JSON.stringify(messages));
    const { triangles, min, max, parts } = geometry(document, binary);
    assert.ok(triangles > 0 && triangles <= budget, `${triangles} triangles exceeds ${budget}`);
    assert.ok(bytes.length <= maxBytes);
    const materials = document.materials.map(material => material.name);
    assert.equal(new Set(materials).size, materials.length);
    assert.ok(materials.every(name => palette.has(name)), materials.join(', '));
    checkDimensions(name, min, max, parts, document, binary);
    const sheet = `reviews/${name}.png`;
    const sheetUrl = new URL(sheet, root);
    const png = await readFile(sheetUrl);
    assert.equal(png.toString('hex', 0, 8), '89504e470d0a1a0a');
    assert.deepEqual([png.readUInt32BE(16), png.readUInt32BE(20)], [1188, 596]);
    assert.ok((await stat(sheetUrl)).mtimeMs >= (await stat(url)).mtimeMs, 'Stale render');
    models.push({
      file, triangles, triangle_budget: budget, bytes: bytes.length,
      size_m: metres(max.map((value, axis) => value - min[axis])),
      bounds_m: { min: metres(min), max: metres(max) },
      materials, parts, sha256: sha256(bytes),
      validator: { result: 'PASS', errors, warnings, version: report.validatorVersion },
      review: { file: sheet, sha256: sha256(png), engine: 'Cycles CPU', views: 6 },
    });
    console.log(`PASS ${file} ${triangles}/${budget} triangles ${bytes.length} B`);
  } catch (error) {
    failures += 1;
    console.error(`FAIL ${file} ${error.message}`);
  }
}

if (failures) {
  process.exitCode = 1;
} else {
  await writeFile(new URL('models.json', root), `${JSON.stringify(models, null, 2)}\n`);
}

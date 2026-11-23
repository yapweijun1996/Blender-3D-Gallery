import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {readFile, writeFile, unlink} from 'node:fs/promises';
import validator from '../../../node_modules/gltf-validator/index.js';

const specs = {
  flower_dome: {budget: 9000, size: [130,38,100]},
  cloud_forest: {budget: 11000, size: [100,58,80]},
};
const allowed = new Set([
  'paint', 'glass', 'window', 'wall', 'roof', 'concrete', 'metal', 'chrome',
  'trim', 'stone', 'water', 'leaf', 'trunk', 'light', 'lamp_emissive', 'rubber', 'plate',
]);
const local = file => new URL(file, import.meta.url);
const hash = data => createHash('sha256').update(data).digest('hex');
const close = (actual, expected, tolerance, label) => {
  assert(Math.abs(actual - expected) <= tolerance, `${label}: ${actual} vs. ${expected}`);
};
const bounds = records => ({
  min: [0, 1, 2].map(i => Math.min(...records.map(record => record.min[i]))),
  max: [0, 1, 2].map(i => Math.max(...records.map(record => record.max[i]))),
});
const round = values => values.map(value => +value.toFixed(3));

const staging = local('.render-evidence.json');
const fresh = await readFile(staging, 'utf8').then(JSON.parse, error => {
  if (error.code === 'ENOENT') return null;
  throw error;
});
const prior = fresh ? null : JSON.parse(await readFile(local('models.json'), 'utf8'));
const models = [];

for (const [name, {budget, size}] of Object.entries(specs)) {
  const file = `${name}.glb`;
  const bytes = await readFile(local(file));
  const report = await validator.validateBytes(bytes, {uri: file});
  assert.equal(report.issues.numErrors, 0, JSON.stringify(report.issues.messages));
  assert.equal(report.issues.numWarnings, 0, JSON.stringify(report.issues.messages));
  assert.equal(bytes.readUInt32LE(0), 0x46546c67);
  assert.equal(bytes.readUInt32LE(4), 2);
  assert.equal(bytes.readUInt32LE(8), bytes.length);
  assert.equal(bytes.readUInt32LE(16), 0x4e4f534a);
  assert(bytes.length <= Math.floor(1.8 * 1024 * 1024));
  const json = JSON.parse(bytes.toString('utf8', 20, 20 + bytes.readUInt32LE(12)));
  assert.equal(json.buffers.length, 1);
  assert.equal(json.buffers[0].uri, undefined);
  for (const key of ['animations', 'skins', 'cameras', 'images', 'textures', 'extensionsRequired']) {
    assert(!json[key]?.length, `${file}: unexpected ${key}`);
  }
  assert(!json.extensions?.KHR_lights_punctual);
  assert.equal(json.nodes.length, json.meshes.length);
  assert.equal(json.scenes[json.scene].nodes.length, json.nodes.length);
  assert.equal(new Set(json.nodes.map(node => node.mesh)).size, json.nodes.length);
  const materials = json.materials.map(material => material.name).sort();
  assert(materials.every(material => allowed.has(material)));
  assert.equal(new Set(materials).size, materials.length);
  for (const material of json.materials.filter(material => ['glass', 'window'].includes(material.name))) {
    assert.equal(material.alphaMode, 'BLEND', `${material.name} must show the interior`);
  }

  const parts = json.nodes.map(node => {
    for (const key of ['matrix', 'rotation', 'scale', 'translation', 'children', 'skin', 'camera']) {
      assert.equal(node[key], undefined, `${node.name}: unexpected ${key}`);
    }
    const mesh = json.meshes[node.mesh];
    assert.equal(mesh.name, node.name);
    let triangles = 0;
    const accessors = mesh.primitives.map(primitive => {
      assert.equal(primitive.mode ?? 4, 4);
      triangles += json.accessors[primitive.indices].count / 3;
      return json.accessors[primitive.attributes.POSITION];
    });
    return {name: node.name, triangles, ...bounds(accessors)};
  });
  assert.equal(new Set(parts.map(part => part.name)).size, parts.length);
  const triangles = parts.reduce((sum, part) => sum + part.triangles, 0);
  assert(triangles <= budget, `${file}: ${triangles} exceeds ${budget}`);
  const {min, max} = bounds(parts);
  close(min[1], 0, .001, `${file} ground`);
  for (const axis of [0, 2]) {
    close(min[axis] + max[axis], 0, .08, `${file} horizontal origin`);
  }
  const measured = max.map((value, i) => value - min[i]);
  measured.forEach((value, i) => close(value, size[i], .10, `${file} dimension ${i}`));
  const get = label => {
    const part = parts.find(part => part.name === label);
    assert(part, `${file}: missing part ${label}`);
    return part;
  };
  assert(get('Front entrance canopy and columns').min[2] > 0);
  assert(get('Front entrance glazing and mullions').min[2] > 0);
  assert(get('Radial outer steel arches').triangles > 1000);
  if (name === 'cloud_forest') {
    const mountain = get('Cloud Mountain');
    close(mountain.max[1], 35, .001, 'Cloud Mountain summit');
    close(mountain.max[1] - mountain.min[1], 35, .25, 'Cloud Mountain height');
    get('Indoor waterfall and plunge pool');
    get('Cloud Walk and Tree Top Walk');
  }
  const capture = fresh?.[name] ?? prior.models.find(model => model.file === file).contact_sheet;
  assert.equal(capture.glb_sha256, hash(bytes), `${file}: stale render`);
  const png = await readFile(local(capture.file));
  assert.equal(capture.sha256, hash(png), `${file}: sheet has changed`);
  assert.equal(capture.views.length, 6);
  assert.equal(png.readUInt32BE(16), 1994);
  assert.equal(png.readUInt32BE(20), 847);
  models.push({
    file, triangles, triangle_budget: budget, bytes: bytes.length,
    size_m: Object.fromEntries(['x','y','z'].map((axis, i) => [axis, round(measured)[i]])),
    materials, parts: parts.map(part => ({...part, min: round(part.min), max: round(part.max)})),
    validator: {
      version: report.validatorVersion, errors: report.issues.numErrors,
      warnings: report.issues.numWarnings, infos: report.issues.numInfos, hints: report.issues.numHints,
    },
    contact_sheet: capture,
  });
  console.log(file, triangles, bytes.length, round(measured), '0 errors / 0 warnings');
}
await writeFile(local('models.json'),
                JSON.stringify({units: 'metres', up: '+Y', front: '+Z', main_axis: 'X', models}, null, 2) + '\n');
if (fresh) await unlink(staging);

import {readFile, writeFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import assert from 'node:assert/strict';
import validator from '../../../node_modules/gltf-validator/index.js';

const budgets = {
  artscience_museum: 9000,
  helix_bridge: 12000,
  supertree_tall: 4000,
  supertree_mid: 4000,
  supertree_short: 4000,
  skyway_segment: 800,
};
const allowedMaterials = new Set([
  'paint', 'glass', 'window', 'wall', 'roof', 'concrete', 'metal', 'chrome',
  'trim', 'stone', 'water', 'leaf', 'trunk', 'light', 'lamp_emissive', 'rubber', 'plate',
]);
const assetUrl = path => new URL(path, import.meta.url);
const hash = bytes => createHash('sha256').update(bytes).digest('hex');
const evidence = JSON.parse(await readFile(assetUrl('renders/evidence.json'), 'utf8'));
const closeTo = (value, expected, tolerance, label) => {
  assert(Math.abs(value - expected) <= tolerance, `${label}: ${value} vs. ${expected}`);
};
const bounds = accessors => ({
  min: [0, 1, 2].map(axis => Math.min(...accessors.map(a => a.min[axis]))),
  max: [0, 1, 2].map(axis => Math.max(...accessors.map(a => a.max[axis]))),
});

const models = [];
for (const [name, budget] of Object.entries(budgets)) {
  const file = `${name}.glb`;
  const bytes = await readFile(assetUrl(file));
  const report = await validator.validateBytes(new Uint8Array(bytes), {uri: file});
  assert.equal(report.issues.numErrors, 0, JSON.stringify(report.issues.messages));
  assert.equal(report.issues.numWarnings, 0, JSON.stringify(report.issues.messages));
  assert.equal(bytes.readUInt32LE(0), 0x46546c67);
  assert.equal(bytes.readUInt32LE(4), 2);
  assert.equal(bytes.readUInt32LE(8), bytes.length);
  assert.equal(bytes.readUInt32LE(16), 0x4e4f534a);
  const json = JSON.parse(bytes.toString('utf8', 20, 20 + bytes.readUInt32LE(12)));
  assert.equal(json.buffers.length, 1);
  assert.equal(json.buffers[0].uri, undefined);
  for (const key of ['animations', 'skins', 'cameras', 'images', 'textures']) {
    assert(!json[key]?.length, `${file}: unexpected ${key}`);
  }
  assert(!json.extensions?.KHR_lights_punctual, `${file}: unexpected lights`);
  assert(!json.extensionsRequired?.length, `${file}: required runtime extension`);
  assert(json.nodes.length === json.meshes.length);
  assert.equal(new Set(json.nodes.map(n => n.mesh)).size, json.meshes.length);
  assert.equal(json.scenes[json.scene].nodes.length, json.nodes.length);
  for (const node of json.nodes) {
    for (const key of ['matrix', 'rotation', 'scale', 'translation', 'children', 'skin', 'camera']) {
      assert.equal(node[key], undefined, `${node.name}: unexpected ${key}`);
    }
  }
  const materials = json.materials.map(m => m.name).sort();
  assert(materials.every(material => allowedMaterials.has(material)));
  const parts = json.nodes.map(node => {
    const mesh = json.meshes[node.mesh];
    const positions = [];
    let triangles = 0;
    for (const primitive of mesh.primitives) {
      assert.equal(primitive.mode ?? 4, 4);
      positions.push(json.accessors[primitive.attributes.POSITION]);
      triangles += json.accessors[primitive.indices].count / 3;
    }
    return {name: node.name, triangles, ...bounds(positions)};
  });
  const triangles = parts.reduce((sum, part) => sum + part.triangles, 0);
  assert(triangles <= budget, `${file}: ${triangles} triangles exceeds ${budget}`);
  assert(bytes.length <= Math.floor(1.8 * 1024 * 1024), `${file} exceeds byte budget`);
  assert.equal(new Set(parts.map(p => p.name)).size, parts.length);
  const {min, max} = bounds(parts);
  closeTo(min[1], 0, .001, `${file} ground`);
  for (const axis of [0, 2]) {
    closeTo(min[axis] + max[axis], 0, .001, `${file} horizontal origin`);
  }
  const named = prefix => parts.filter(p => p.name.startsWith(prefix));
  if (name === 'artscience_museum') {
    assert.equal(named('Finger ').length, 10);
    closeTo(Math.min(...named('Finger ').map(p => p.max[1])), 21, .005, 'shortest finger');
    const shellTops = json.meshes.filter(m => m.name.startsWith('Finger ')).map(mesh =>
      Math.max(...mesh.primitives.filter(p => json.materials[p.material].name === 'roof')
        .map(p => json.accessors[p.attributes.POSITION].max[1])));
    closeTo(Math.min(...shellTops), 21, .005, 'shortest FRP shell');
    closeTo(Math.max(...shellTops), 60, .005, 'highest FRP shell');
    // Check the overall envelope separately from the nominal shell heights.
    closeTo(max[1], 60, .1, 'highest museum finger including its external glazing');
    assert(named('South entrance')[0].min[2] > 0);
  }
  if (name === 'helix_bridge') {
    assert.equal(named('Viewing pod ').length, 4);
    assert.equal(named('Deck span ').length, 5);
    assert(named('Outer helix | 6').length && named('Inner helix | 5').length);
    assert(named('Viewing pod ').every(p => p.max[2] > named('Deck span 03')[0].max[2]));
    closeTo(max[0] - min[0], 280, 10, 'bridge straight-line footprint');
  }
  if (name.startsWith('supertree_')) {
    closeTo(max[1], {supertree_tall:50, supertree_mid:35, supertree_short:25}[name], .025, name);
  }
  if (name === 'skyway_segment') {
    closeTo(max[0] - min[0], 20, .75, 'skyway straight-line footprint');
  }
  const capture = evidence[file];
  assert.equal(capture.glb_sha256, hash(bytes), `${file}: stale render`);
  assert.equal(capture.sha256, hash(await readFile(assetUrl(capture.file))));
  assert.equal(capture.views.length, 6);
  models.push({
    file, triangles, triangle_budget: budget, bytes: bytes.length,
    size_m: Object.fromEntries(['x','y','z'].map((axis, i) => [axis, +(max[i] - min[i]).toFixed(3)])),
    materials, parts,
    validator: {
      version: report.validatorVersion,
      errors: report.issues.numErrors, warnings: report.issues.numWarnings,
      infos: report.issues.numInfos, hints: report.issues.numHints,
    },
    sha256: capture.glb_sha256, contact_sheet: capture.file,
  });
  console.log(file, triangles, bytes.length, models.at(-1).size_m, '0 errors / 0 warnings');
}
await writeFile(assetUrl('models.json'), JSON.stringify({units:'metres', up:'+Y', front:'+Z', models}, null, 2)+'\n');

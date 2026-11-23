import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { readFile, writeFile } from 'node:fs/promises';
import validator from '../../../node_modules/gltf-validator/index.js';

const budget = {checkpoint_lane: 3500, checkpoint_canopy: 4000, checkpoint_building: 6000};
const approved = new Set('paint glass window wall roof concrete metal chrome trim stone water leaf trunk light lamp_emissive rubber plate'.split(' '));
const manifestPath = new URL('models.json', import.meta.url);
const load = (file) => readFile(new URL(file, import.meta.url));
const hash = (data) => createHash('sha256').update(data).digest('hex');
async function loadOptional(file) {
  try {
    return JSON.parse(await load(file));
  } catch (error) {
    if (error.code !== 'ENOENT') throw error;
  }
}

const previous = await loadOptional('models.json');
const captures = {
  ...Object.fromEntries((previous?.models ?? []).map(model =>
    [model.file.replace('.glb', ''), model.contact_sheet])),
  ...await loadOptional('.render-evidence.json'),
};

function near(actual, expected, label, tolerance = .001) {
  assert(Math.abs(actual - expected) <= tolerance, `${label}: got ${actual}, expected ${expected}`);
}

function bounds(parts) {
  return {
    min: [0, 1, 2].map(i => Math.min(...parts.map(part => part.min[i]))),
    max: [0, 1, 2].map(i => Math.max(...parts.map(part => part.max[i]))),
  };
}

function points(glb, index, floatsOnly = false) {
  const acc = glb.json.accessors[index];
  const view = glb.json.bufferViews[acc.bufferView];
  const channels = {VEC3: 3, VEC4: 4}[acc.type];
  const bytes = {5121: 1, 5123: 2, 5126: 4}[acc.componentType];
  assert(channels && bytes && (!floatsOnly || acc.componentType === 5126));
  return Array.from({length: acc.count}, (_, vertex) => {
    const start = glb.binOffset + (view.byteOffset ?? 0) + (acc.byteOffset ?? 0)
      + vertex * (view.byteStride ?? channels * bytes);
    return Array.from({length: channels}, (_, c) => {
      const offset = start + c * bytes;
      if (bytes === 4) return glb.data.readFloatLE(offset);
      const raw = bytes === 1 ? glb.data.readUInt8(offset) : glb.data.readUInt16LE(offset);
      return acc.normalized ? raw / (256 ** bytes - 1) : raw;
    });
  });
}

function partInfo(json, node) {
  const mesh = json.meshes[node.mesh];
  const translation = node.translation ?? [0, 0, 0];
  let triangles = 0;
  const partBounds = mesh.primitives.map(primitive => {
    assert.equal(primitive.mode ?? 4, 4);
    triangles += json.accessors[primitive.indices].count / 3;
    const accessor = json.accessors[primitive.attributes.POSITION];
    return {
      min: accessor.min.map((x, i) => x + translation[i]),
      max: accessor.max.map((x, i) => x + translation[i]),
    };
  });
  return {name: node.name, triangles, ...bounds(partBounds)};
}

function checkLane(get, glb) {
  const island = get('booth_island');
  const deck = get('lane_deck');
  const booth = get('booth_shell');
  const arm = get('boom_arm');
  const pin = glb.json.nodes.find(node => node.name === 'boom_arm').translation;
  for (const name of ['booth_glazing', 'booth_counter', 'bollards', 'inspection_kiosk', 'boom_housing'])
    get(name);
  near(deck.max[2] - deck.min[2], 9, 'lane length');
  near(.90 - deck.min[0], 3.3, 'clear lane width');
  near(island.min[0], .90, 'island kerb position', .011);
  near(booth.max[0] - booth.min[0], 1.2, 'booth width');
  near(booth.max[1] - booth.min[1], 2.6, 'booth height');
  near(booth.max[2] - booth.min[2], 2, 'booth depth');
  [.86, 1.02, 2.65].forEach((value, i) => near(pin[i], value, 'boom pivot'));
  near(arm.max[0], pin[0], 'arm starts at node pivot');
  near(arm.min[0], pin[0] - 3.2, 'arm tip in the closed pose');
  const mesh = glb.json.meshes[glb.json.nodes.find(node => node.name === 'boom_arm').mesh];
  const sortedArmMaterials = mesh.primitives.map(item => glb.json.materials[item.material].name).sort();
  assert.deepEqual(sortedArmMaterials, ['paint','wall']);
  assert.equal(glb.json.materials.find(material => material.name === 'glass').alphaMode, 'BLEND');
}

function checkCanopy(get, glb) {
  const roof = get('canopy_roof');
  get('lane_gantry');
  get('portal_trusses');
  near(roof.max[0] - roof.min[0], 30, 'canopy span');
  near(roof.max[1], 8, 'canopy height', .025);
  const columns = glb.json.meshes[glb.json.nodes.find(node => node.name === 'portal_columns').mesh];
  for (const primitive of columns.primitives) {
    assert(points(glb, primitive.attributes.POSITION, true).every(([x]) => Math.abs(x) >= 14.399),
      'support intrudes into a lane tile');
  }
  const states = [];
  for (let n = 1; n <= 6; n++) {
    const prefix = `lane_${String(n).padStart(2, '0')}_`;
    get(prefix + 'number');
    const lamp = get(prefix + 'control');
    get(prefix + 'traffic_light');
    near((lamp.min[0] + lamp.max[0])/2 - .36, (n - 3.5)*4.8 - .75, 'lane center registration');
    for (const part of ['control','traffic_light']) {
      const node = glb.json.nodes.find(item => item.name === prefix + part);
      const primitive = glb.json.meshes[node.mesh].primitives.find(item =>
        glb.json.materials[item.material].name === 'lamp_emissive');
      const signal = points(glb, primitive.attributes.COLOR_0)[0];
      const red = signal[0] > .85 && signal[1] < .15;
      const green = signal[1] > .85 && signal[0] < .15;
      assert(red || green, prefix + ' lacks a red or green signal');
      assert.equal(red, n === 3 || n === 6, prefix + ' differs from the specified kit state');
      if (part === 'control') states.push(red ? 'closed' : 'open');
    }
  }
  return states;
}

function checkBuilding(get) {
  const base = get('building_podium');
  const facade = get('curved_glass_facade');
  const visor = get('projecting_entrance_roof');
  for (const name of ['upper_hall_glazing', 'west_wing', 'east_wing', 'entrance_doors', 'main_roof'])
    get(name);
  near(base.max[0] - base.min[0], 60, 'building length');
  assert(facade.max[2] > 0 && facade.max[2] - facade.min[2] > 3, 'curved lobby facade');
  assert(visor.max[2] - facade.max[2] > 1.8, 'projecting roof eave');
}

const models = [];
for (const [name, triangleBudget] of Object.entries(budget)) {
  const file = name + '.glb';
  const data = await load(file);
  const issues = (await validator.validateBytes(new Uint8Array(data), {uri: file})).issues;
  assert.equal(issues.numErrors + issues.numWarnings, 0, JSON.stringify(issues.messages));
  assert.equal(data.readUInt32LE(0), 0x46546c67);
  assert.equal(data.readUInt32LE(4), 2);
  assert.equal(data.readUInt32LE(8), data.length);
  assert.equal(data.readUInt32LE(16), 0x4e4f534a);
  const end = 20 + data.readUInt32LE(12);
  const json = JSON.parse(data.toString('utf8', 20, end));
  assert.equal(data.readUInt32LE(end + 4), 0x004e4942);
  assert.equal(json.buffers.length, 1);
  assert.equal(json.buffers[0].uri, undefined);
  for (const key of ['animations','skins','cameras','images','textures'])
    assert(!json[key]?.length, file + ' has ' + key);
  assert(!json.extensions?.KHR_lights_punctual);
  assert(!json.extensionsRequired?.length);
  assert.equal(json.nodes.length, json.meshes.length);
  assert.equal(new Set(json.nodes.map(node => node.mesh)).size, json.meshes.length);
  assert.equal(json.scenes[json.scene].nodes.length, json.nodes.length);
  for (const node of json.nodes) {
    for (const key of ['matrix','rotation','scale','children','camera','skin'])
      assert.equal(node[key], undefined, node.name + ' has ' + key);
    if (node.name !== 'boom_arm') assert.equal(node.translation, undefined);
  }

  const materials = json.materials.map(item => item.name).sort();
  assert.equal(new Set(materials).size, materials.length);
  assert(materials.every(material => approved.has(material)));
  const parts = json.nodes.map(node => partInfo(json,node));
  const tris = parts.reduce((sum, part) => sum + part.triangles, 0);
  assert(tris <= triangleBudget, file + ' exceeds triangle budget');
  assert(data.length <= Math.floor(1.8 * 1024**2), file + ' exceeds file budget');
  assert.equal(new Set(parts.map(part => part.name)).size, parts.length);
  const {min,max} = bounds(parts);
  near(min[1], 0, file + ' ground');
  near(min[0] + max[0], 0, file + ' centered width');
  near(min[2] + max[2], 0, file + ' centered depth');
  const get = partName => {
    const result = parts.find(part => part.name === partName);
    assert(result, 'missing part: ' + partName);
    return result;
  };
  const glb = {data, json, binOffset: end + 8};
  const specific = {};
  if (name === 'checkpoint_lane') {
    checkLane(get,glb);
    specific.driveable_width_m = 3.3;
    specific.repeat_pitch_m = 4.8;
    specific.boom = {node:'boom_arm', pivot_m:[.86,1.02,2.65], length_m:3.2,
      hinge_axis_local:[0,0,1], lift_rotation_degrees:-90};
  }
  if (name === 'checkpoint_canopy') specific.lane_states = checkCanopy(get,glb);
  if (name === 'checkpoint_building') checkBuilding(get);
  const capture = captures[name];
  assert.equal(capture.glb_sha256, hash(data), file + ' render is stale');
  assert.equal(capture.sha256, hash(await load(capture.file)), file + ' render image changed');
  assert.equal(capture.views.length, 6);
  assert.equal(capture.threads, 2);
  const round = value => Number(value.toFixed(3));
  models.push({
    file, triangles:tris, triangle_budget:triangleBudget, bytes:data.length,
    size_m:Object.fromEntries(['x','y','z'].map((axis,i) => [axis,round(max[i]-min[i])])),
    materials, parts:parts.map(part => ({...part,min:part.min.map(round),max:part.max.map(round)})),
    validator:{name:'gltf-validator',errors:issues.numErrors,warnings:issues.numWarnings,
      infos:issues.numInfos,hints:issues.numHints},
    sha256:hash(data), contact_sheet:capture, ...specific,
  });
  console.log(`${file}  ${tris}/${triangleBudget} tris  ${data.length} bytes  glTF Validator ${issues.numErrors} errors, ${issues.numWarnings} warnings`);
}
await writeFile(manifestPath, JSON.stringify({
  authoring:'Blender 5.1.2',
  source_sha256:hash(await load('build_models.py')),
  units:'metres',
  up:'+Y',
  front:'+Z',
  road_axis:'+Z',
  origin:'center of the ground footprint',
  models,
}, null, 2) + '\n');

import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { join, relative } from 'node:path';
import validator from 'gltf-validator';
import { here, names, root, source, work } from './run.mjs';
import { readGlb } from './pack_npc.mjs';

const evidence = join(here, 'evidence');
mkdirSync(evidence, { recursive: true });
const json = p => JSON.parse(readFileSync(p, 'utf8'));
const save = (p, value) => writeFileSync(p, JSON.stringify(value, null, 2) + '\n');
const sha = bytes => createHash('sha256').update(bytes).digest('hex');
const clips = ['rest', 'walk', 'run', 'wave', 'jump', 'idle', 'nod', 'dance',
  'sit_down', 'sit_idle', 'stand_up', 'hold_item'];
const slots = {
  'hair-bob': ['hair', 2400], 'hair-spiky': ['hair', 2400], 'hair-sidepart': ['hair', 2400],
  'shoes-sneakers': ['shoes', 1500], 'top-tshirt': ['top', 2600],
  'bottom-jeans': ['bottom', 2600], 'top-dress': ['top', 3000],
};

function accessor(asset, index, components) {
  const { json: doc, bin } = asset;
  const a = doc.accessors[index];
  const v = doc.bufferViews[a.bufferView];
  const readers = {
    5121: [1, 'readUInt8', 255], 5123: [2, 'readUInt16LE', 65535],
    5125: [4, 'readUInt32LE', 4294967295], 5126: [4, 'readFloatLE', 1],
  };
  const [size, method, range] = readers[a.componentType];
  const offset = (v.byteOffset ?? 0) + (a.byteOffset ?? 0);
  const stride = v.byteStride ?? components * size;
  return Array.from({ length: a.count }, (_, i) => Array.from({ length: components }, (_, k) =>
    bin[method](offset + stride*i + size*k)/(a.normalized ? range : 1)));
}

function jpegSize(image) {
  assert.equal(image.readUInt16BE(0), 0xffd8);
  for (let p = 2; p + 9 < image.length;) {
    assert.equal(image[p], 0xff);
    const marker = image[p+1];
    if ([0xc0, 0xc1, 0xc2].includes(marker)) return [image.readUInt16BE(p+7), image.readUInt16BE(p+5)];
    p += 2 + image.readUInt16BE(p+2);
  }
  throw new Error('Missing JPEG dimensions');
}

function inspect(asset, allowNeutralMorphs = false) {
  const { bytes, json: doc, bin } = asset;
  assert.equal(doc.skins.length, 1);
  const skin = doc.skins[0];
  const joints = skin.joints.map(id => doc.nodes[id].name);
  assert.equal(joints.length, 65);
  assert.equal(new Set(joints).size, 65);
  assert.ok(joints.every(n => n.startsWith('mixamorig:')));
  assert.ok(!(doc.animations?.length));
  assert.ok(doc.nodes.every(n => !n.weights || n.weights.every(w => w === 0)));
  assert.ok(doc.meshes.every(m => !m.weights || m.weights.every(w => w === 0)));
  const primitives = doc.meshes.flatMap(mesh => mesh.primitives);
  const morphTargets = Math.max(...primitives.map(p => p.targets?.length ?? 0));
  let triangles = 0, maxInfluences = 0, maxWeightError = 0;
  for (const primitive of primitives) {
    const p = primitive.attributes;
    assert.equal(primitive.mode ?? 4, 4);
    assert.ok(!('JOINTS_1' in p || 'WEIGHTS_1' in p));
    if (!allowNeutralMorphs) assert.ok(!primitive.targets?.length);
    assert.equal((doc.materials[primitive.material].alphaMode ?? 'OPAQUE'), 'OPAQUE');
    triangles += doc.accessors[primitive.indices].count / 3;
    const weights = accessor(asset, p.WEIGHTS_0, 4);
    const bones = accessor(asset, p.JOINTS_0, 4);
    assert.equal(weights.length, bones.length);
    assert.equal(weights.length, doc.accessors[p.POSITION].count);
    for (let i = 0; i < weights.length; i++) {
      assert.ok(weights[i].every(w => w >= 0 && w <= 1));
      assert.ok(bones[i].every(n => n >= 0 && n < joints.length));
      maxInfluences = Math.max(maxInfluences, weights[i].filter(w => w > 0).length);
      maxWeightError = Math.max(maxWeightError, Math.abs(weights[i].reduce((sum, w) => sum+w, 0) - 1));
    }
  }
  assert.ok(maxInfluences <= 4 && maxWeightError < 1e-5);
  const textures = (doc.images ?? []).map(image => {
    const view = doc.bufferViews[image.bufferView];
    const data = bin.subarray(view.byteOffset, (view.byteOffset ?? 0) + view.byteLength);
    const size = image.mimeType === 'image/png' ? [data.readUInt32BE(16), data.readUInt32BE(20)] : jpegSize(data);
    return { name: image.name, size, mimeType: image.mimeType, bytes: view.byteLength };
  });
  return { bytes: bytes.length, sha256: sha(bytes), triangles, primitives: primitives.length,
    joints, maxInfluences, maxWeightError, textures, morphTargets,
    uv: primitives.some(p => p.attributes.TEXCOORD_0 !== undefined),
    vertexColor: primitives.some(p => p.attributes.COLOR_0 !== undefined) };
}

function inverseBinds(asset) {
  return accessor(asset, asset.json.skins[0].inverseBindMatrices, 16);
}

function motion(name, mode, hash) {
  const armsDir = join(root, 'output/modular-chibi-parts');
  const masterHash = sha(readFileSync(join(armsDir, 'master/GJH_Chibi_Master_rigged.blend')));
  const motionHash = sha(readFileSync(join(armsDir, 'body-fix/motion_fixed.glb')));
  const actionsHash = sha(readFileSync(join(armsDir, 'actions-fix/actions_fixed.glb')));
  const reports = {};
  for (const family of ['legacy', 'actions']) {
    reports[family] = {};
    for (const metric of ['vertices', 'triangles']) {
      const path = join(work, mode, name, family, metric, family + '-' + metric + '.json');
      const result = json(path);
      assert.equal(result.glb_sha256, hash, path);
      assert.equal(result.master_sha256, masterHash, path);
      assert.equal(result.motion_sha256, motionHash, path);
      assert.equal(result.actions_sha256, family === 'actions' ? actionsHash : null, path);
      assert.deepEqual(Object.keys(result.results), family === 'actions' ? clips : clips.slice(0, 8));
      reports[family][metric] = result;
    }
  }
  return { masterSha256: masterHash, motionSha256: motionHash, actionsSha256: actionsHash, reports };
}

function combine(raw) {
  const { actions, legacy } = raw.reports;
  return Object.fromEntries(clips.map(clip => {
    const appended = actions.vertices.results[clip];
    const overlap = actions.triangles.results[clip];
    const dense = legacy.vertices.results[clip];
    const coarse = legacy.triangles.results[clip];
    return [clip, {
      inside: Math.max(appended[0], dense?.[0] ?? 0),
      overlap: Math.max(overlap[0], coarse?.[0] ?? 0),
      // The shared checker rounds to 0.1 mm for posed clips. Its values remain
      // available in the raw report. Use the all-integer precise minima here.
      minimumMm: 1000*Math.min(appended[1], overlap[1]),
      frames: clip === 'rest' ? 1 : actions.vertices.frames[clip].length,
    }];
  }));
}

function motionFailures(name, baseline, npc) {
  const failures = [];
  for (const clip of clips) {
    const row = npc[clip], source = baseline[clip];
    const shirt = name === 'top-tshirt';
    if (row.inside > (shirt ? Math.min(21, source.inside) : 0)) failures.push(`${clip}: inside ${row.inside}`);
    if (row.overlap > (shirt ? source.overlap : 0)) failures.push(`${clip}: overlap ${row.overlap}`);
    if (row.minimumMm < (shirt ? -1.4 : name === 'top-dress' ? .5 : 0)) {
      failures.push(`${clip}: minimum ${row.minimumMm.toFixed(4)} mm`);
    }
  }
  return failures;
}

const bodyAsset = readGlb(join(root, 'models/chibi-dressup/base_body.glb'));
const body = inspect(bodyAsset, true);
assert.ok(body.bytes <= 1.5*2**20 && body.triangles <= 10000);
assert.ok(body.textures.every(t => Math.max(...t.size) <= 1024));
const bodyValidation = await validator.validateBytes(new Uint8Array(bodyAsset.bytes), { uri: 'base_body.glb' });
assert.equal(bodyValidation.issues.numErrors, 0);
assert.equal(bodyValidation.issues.numWarnings, 0);
save(join(evidence, 'base-body-validator.json'), bodyValidation);
const manifest = { version: 1, modules: [] };
const report = { body: { file: 'models/chibi-dressup/base_body.glb', ...body }, modules: {}, outfits: {} };
const motionReport = {};
const geometry = json(join(work, 'geometry.json'));
const failed = [];
for (const name of names) {
  const originalAsset = readGlb(source(name));
  const file = 'npc-' + name + '.glb';
  const npcAsset = readGlb(join(here, file));
  const before = inspect(originalAsset);
  const after = inspect(npcAsset);
  assert.deepEqual([...after.joints].sort(), [...before.joints].sort());
  assert.deepEqual([...after.joints].sort(), [...body.joints].sort());
  assert.equal(after.uv, before.uv);
  assert.equal(after.vertexColor, before.vertexColor);
  const sourceMatrices = inverseBinds(originalAsset), npcMatrices = inverseBinds(npcAsset);
  const maxInverseBindError = Math.max(...before.joints.flatMap((name, i) =>
    sourceMatrices[i].map((v, k) => Math.abs(v - npcMatrices[after.joints.indexOf(name)][k]))));
  assert.ok(maxInverseBindError < 1e-5);
  const [slot, limit] = slots[name];
  assert.ok(after.triangles <= limit);
  assert.ok(after.bytes <= 600_000 && after.bytes < before.bytes);
  assert.ok(after.textures.every(t => Math.max(...t.size) <= 512));
  const validation = await validator.validateBytes(new Uint8Array(npcAsset.bytes), { uri: file });
  if (validation.issues.numErrors || validation.issues.numWarnings) failed.push(name + ' Khronos');
  save(join(evidence, file.replace('.glb', '-validator.json')), validation);
  assert.equal(geometry[name].after.triangles, after.triangles);
  assert.equal(geometry[name].after.sha256, after.sha256);
  assert.equal(geometry[name].before.sha256, before.sha256);
  assert.deepEqual(geometry[name].before.topology, geometry[name].after.topology);
  manifest.modules.push({ id: 'npc-' + name, slot, file, triangles: after.triangles,
    bytes: after.bytes, sha256: after.sha256, source: relative(root, source(name)),
    sourceSha256: before.sha256, status: 'pending',
    bodyIds: ['neutral-body'], ...(name === 'top-dress' ? { excludesSlots: ['bottom'] } : {}) });
  const dir = join(work, name);
  const build = { decimation: json(join(dir, 'decimation.json')) };
  if (['shoes-sneakers','top-tshirt','bottom-jeans','top-dress'].includes(name)) {
    build.motionGuard = json(join(dir, 'guard.json'));
  }
  if (['bottom-jeans','top-dress'].includes(name)) {
    const { chosen_iteration, moved_vertices, max_displacement_m, frames } = json(join(dir, 'fit.json'));
    build.fit = { chosen_iteration, moved_vertices, max_displacement_m, frames };
  }
  report.modules[name] = { before, after, maxInverseBindError, topology: geometry[name], build };
  const baseRaw = motion(name, 'baseline', before.sha256);
  const npcRaw = motion(name, 'check', after.sha256);
  const baseline = combine(baseRaw), candidate = combine(npcRaw);
  const failures = motionFailures(name, baseline, candidate);
  failed.push(...failures.map(f => name + ' ' + f));
  motionReport[name] = { baseline, npc: candidate, failures };
  // Keep source and output frame evidence alongside the summarized comparison.
  const motionDir = join(evidence, 'motion');
  mkdirSync(motionDir, { recursive: true });
  save(join(motionDir, name + '.json'), { npc: npcRaw, baseline: baseRaw });
}
for (const [id, parts] of Object.entries({
  'spiky-tshirt-jeans': ['hair-spiky','top-tshirt','bottom-jeans','shoes-sneakers'],
  'bob-dress': ['hair-bob','top-dress','shoes-sneakers'],
  'bob-tshirt-jeans': ['hair-bob','top-tshirt','bottom-jeans','shoes-sneakers'],
  'sidepart-tshirt-jeans': ['hair-sidepart','top-tshirt','bottom-jeans','shoes-sneakers'],
})) {
  const totals = stage => [body, ...parts.map(n => report.modules[n][stage])].reduce((a, asset) =>
    ({ triangles: a.triangles + asset.triangles, primitives: a.primitives + asset.primitives,
       bytes: a.bytes + asset.bytes }), { triangles: 0, primitives: 0, bytes: 0 });
  const after = totals('after');
  assert.ok(after.triangles <= 20000 && after.primitives <= 12);
  report.outfits[id] = { before: totals('before'), after };
}
const modulesBytes = manifest.modules.reduce((sum, row) => sum+row.bytes, 0);
report.budget = { modulesBytes, modulesAndBodyBytes: modulesBytes+body.bytes, maxBytes: 6*2**20 };
assert.ok(report.budget.modulesAndBodyBytes <= report.budget.maxBytes);
report.failures = failed;
save(join(here, 'npc-manifest.json'), manifest);
save(join(evidence, 'asset-report.json'), report);
save(join(evidence, 'motion-summary.json'), motionReport);

const table = ['# Motion checks', '', 'Each cell shows NPC peak inside vertices / peak triangle overlap pairs / minimum signed distance in mm.',
  '', '| Clip | ' + names.join(' | ') + ' |', '|---|' + names.map(() => '---:').join('|') + '|'];
for (const clip of clips) {
  const values = names.map(n => {
    const row = motionReport[n].npc[clip];
    return `${row.inside} / ${row.overlap} / ${row.minimumMm.toFixed(3)}`;
  });
  table.push('| ' + clip + ' | ' + values.join(' | ') + ' |');
}
table.push('', '## T-shirt source and NPC comparison', '',
  '| Clip | Full vertices / pairs / mm | NPC vertices / pairs / mm |', '|---|---:|---:|');
for (const clip of clips) {
  const values = ['baseline','npc'].map(stage => {
    const row = motionReport['top-tshirt'][stage][clip];
    return `${row.inside} / ${row.overlap} / ${row.minimumMm.toFixed(3)}`;
  });
  table.push('| ' + clip + ' | ' + values.join(' | ') + ' |');
}
table.push('', failed.length ? 'Unmet results' : 'All motion and Khronos checks passed.');
for (const failure of failed) table.push('- ' + failure);
writeFileSync(join(evidence, 'motion-summary.md'), table.join('\n') + '\n');
const budgetTable = ['# Wardrobe budgets', '',
  '| Module | Full triangles | NPC triangles | Full bytes | NPC bytes | NPC opaque primitives |',
  '|---|---:|---:|---:|---:|---:|'];
for (const [name, { before, after }] of Object.entries(report.modules)) {
  budgetTable.push(`| ${name} | ${before.triangles} | ${after.triangles} | ${before.bytes} | ${after.bytes} | ${after.primitives} |`);
}
budgetTable.push('', '| Outfit | Full triangles | NPC triangles | Full bytes | NPC bytes | NPC opaque primitives |',
  '|---|---:|---:|---:|---:|---:|');
for (const [name, { before, after }] of Object.entries(report.outfits)) {
  budgetTable.push(`| ${name} | ${before.triangles} | ${after.triangles} | ${before.bytes} | ${after.bytes} | ${after.primitives} |`);
}
budgetTable.push('', `The seven NPC modules total **${modulesBytes} bytes**. With the unchanged body, the total is **${report.budget.modulesAndBodyBytes} bytes**.`);
writeFileSync(join(evidence, 'budget-summary.md'), budgetTable.join('\n') + '\n');
console.log(JSON.stringify({ budget: report.budget, outfits: report.outfits, failures: failed }, null, 2));
process.exitCode = failed.length ? 1 : 0;

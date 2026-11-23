import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { readFile, writeFile } from 'node:fs/promises';
import validator from 'gltf-validator';

const names = new Set([
  'paint', 'glass', 'window', 'wall', 'roof', 'concrete', 'metal', 'chrome',
  'trim', 'stone', 'water', 'leaf', 'trunk', 'light', 'lamp_emissive', 'rubber', 'plate',
]);
const budgets = { merlion: 9000, merlion_park: 5000 };
const sha = (bytes) => createHash('sha256').update(bytes).digest('hex');
const local = (file) => new URL(file, import.meta.url);
const read = (file) => readFile(local(file));
const close = (value, expected) => Math.abs(value - expected) < 1e-4;
const xyz = [0, 1, 2];
const axisExtrema = (parts, key, operation) => xyz.map(i => operation(...parts.map(part => part[key][i])));
const round = (n) => Number(n.toFixed(4));

const output = [];
const failures = [];
for (const [name, budget] of Object.entries(budgets)) {
  const file = name + '.glb';
  const data = await read(file);
  const validatorReport = await validator.validateBytes(new Uint8Array(data), { uri: file });
  const { numErrors, numWarnings, messages } = validatorReport.issues;
  const check = (condition, message) => {
    if (!condition) failures.push(`${file}: ${message}`);
  };

  assert.equal(data.subarray(0, 4).toString(), 'glTF');
  assert.equal(data.readUInt32LE(4), 2);
  assert.equal(data.readUInt32LE(8), data.length);
  const gltf = JSON.parse(data.subarray(20, 20 + data.readUInt32LE(12)));
  const issues = messages.filter(message => message.severity <= 1);
  check(!numErrors && !numWarnings, JSON.stringify(issues));
  check(data.length <= 1.8 * 1024 ** 2, `${data.length} bytes exceeds 1.8 MiB`);
  check(gltf.buffers.length === 1 && !gltf.buffers[0].uri, 'external GLB buffer');
  check(!['skins', 'animations', 'cameras', 'images', 'textures'].some(key => gltf[key]?.length)
    && !gltf.extensionsUsed?.includes('KHR_lights_punctual'), 'unexpected GLB resources');
  check(gltf.asset.generator.includes('v5.1.2'), 'unexpected Blender export version');

  const materials = gltf.materials.map(m => m.name);
  check(materials.every(m => names.has(m)), 'material name outside the palette');
  check(new Set(materials).size === materials.length, 'duplicate material names');
  check(gltf.scenes[gltf.scene].nodes.length === gltf.nodes.length, 'expected flat named mesh hierarchy');
  const parts = gltf.nodes.map(node => {
    check(Number.isInteger(node.mesh) && node.name === gltf.meshes[node.mesh].name
      && !node.matrix && !node.rotation && !node.scale && !node.children, 'unexpected mesh node or transform');
    const counts = [];
    const positions = gltf.meshes[node.mesh].primitives.map(primitive => {
      check((primitive.mode ?? 4) === 4 && Number.isInteger(primitive.material), 'invalid game primitive');
      const accessor = gltf.accessors[primitive.attributes.POSITION];
      counts.push((primitive.indices === undefined ? accessor.count : gltf.accessors[primitive.indices].count)/3);
      return accessor;
    });
    const origin = node.translation ?? [0, 0, 0];
    return {
      name: node.name,
      triangles: counts.reduce((a, b) => a + b, 0),
      origin,
      min: axisExtrema(positions, 'min', Math.min).map((value, i) => value + origin[i]),
      max: axisExtrema(positions, 'max', Math.max).map((value, i) => value + origin[i]),
    };
  });
  const byName = Object.fromEntries(parts.map(part => [part.name, part]));
  const min = axisExtrema(parts, 'min', Math.min);
  const max = axisExtrema(parts, 'max', Math.max);
  const size = max.map((value, i) => value - min[i]);
  const triangles = parts.reduce((sum, part) => sum + part.triangles, 0);
  check(triangles > 0 && triangles <= budget, `${triangles}/${budget} triangles`);
  check(close(min[1], 0), `ground is at ${min[1]} m`);
  check(Object.keys(byName).length === parts.length && parts.length > 6, 'missing, repeated or unsplit mesh parts');
  if (name === 'merlion') {
    const plinth = byName.stone_plinth_and_wave_mosaic;
    check(close(max[1], 8.6), 'main statue height is not 8.6 m');
    check(close(byName.merlion_cub.max[1], 2), 'cub height is not 2 m');
    check(close(plinth.min[0] + plinth.max[0], 0) && close(plinth.min[2] + plinth.max[2], 0),
      'plinth is not centered at the origin');
    check(byName.water_jet?.origin[2] > 0 && byName.water_jet.max[2] > plinth.max[2]
      && byName.lion_head.max[2] > byName.lion_head.origin[2], 'water jet and face must face +Z');
  } else {
    check(close(size[0], 60) && close(size[2], 40) && close(min[0] + max[0], 0)
      && close(min[2] + max[2], 0), 'park footprint must be a centered 60 m by 40 m');
    for (const part of ['waterfront_plaza', 'semicircular_waterfront_platform', 'curved_stone_parapet',
      'stepped_granite_seawall', 'promenade_benches', 'promenade_lamp_posts', 'precast_pier_and_viewing_deck']) {
      check(byName[part]?.triangles > 0, `missing ${part}`);
    }
  }
  const sheet = name + '_contact.png';
  const image = await read(sheet);
  const hash = sha(data);
  check(image.includes(Buffer.from('GLB SHA-256\0' + hash)), 'contact sheet is for another export');
  output.push({
    file,
    triangles,
    triangle_budget: budget,
    bytes: data.length,
    size_m: { x: round(size[0]), y: round(size[1]), z: round(size[2]) },
    materials,
    parts: parts.map(part => ({
      name: part.name, triangles: part.triangles, origin_m: part.origin.map(round),
    })),
    validator: { version: validatorReport.validatorVersion, errors: numErrors, warnings: numWarnings },
    sha256: hash,
    contact_sheet: sheet,
    contact_sheet_sha256: sha(image),
  });
  console.log(file, triangles, data.length, size.map(round),
    `validator ${numErrors} errors / ${numWarnings} warnings`);
}
assert.equal(failures.length, 0, failures.join('\n'));
await writeFile(local('models.json'), JSON.stringify(output, null, 2) + '\n');

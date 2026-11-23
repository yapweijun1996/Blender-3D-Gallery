import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { readFileSync, renameSync, writeFileSync } from 'node:fs';
import validator from 'gltf-validator';

const root = new URL('./', import.meta.url);
const read = name => readFileSync(new URL(name, root));
const sha256 = bytes => createHash('sha256').update(bytes).digest('hex');
const releaseKeys = ['dress', 'jeans'];

function unpack(raw) {
  const end = 20 + raw.readUInt32LE(12);
  return {
    doc: JSON.parse(raw.toString('utf8', 20, end)),
    binary: raw.subarray(end + 8),
    binChunk: raw.subarray(end),
  };
}

function sceneRoot(raw) {
  const { doc, binChunk } = unpack(raw);
  const mesh = doc.nodes.findIndex(node => node.skin !== undefined);
  const parent = doc.nodes.findIndex(node => node.children?.includes(mesh));
  if (parent < 0) return raw;
  const scene = doc.scenes[doc.scene];
  assert.ok(scene.nodes.includes(parent));
  assert.ok(!['matrix', 'translation', 'rotation', 'scale'].some(key => key in doc.nodes[parent]));
  doc.nodes[parent].children = doc.nodes[parent].children.filter(index => index !== mesh);
  scene.nodes.push(mesh);
  const json = Buffer.from(JSON.stringify(doc));
  const length = Math.ceil(json.length / 4) * 4;
  const padded = Buffer.alloc(length, 0x20);
  json.copy(padded);
  const header = Buffer.from(raw.subarray(0, 20));
  header.writeUInt32LE(length, 12);
  header.writeUInt32LE(20 + length + binChunk.length, 8);
  return Buffer.concat([header, padded, binChunk]);
}

function repairDegenerateTangents(raw) {
  const { doc, binary } = unpack(raw);
  let fixed = 0;
  const processed = new Set();
  for (const { attributes } of doc.meshes.flatMap(mesh => mesh.primitives)) {
    if (attributes.TANGENT === undefined || processed.has(attributes.TANGENT)) continue;
    processed.add(attributes.TANGENT);
    const tangent = doc.accessors[attributes.TANGENT];
    const normal = doc.accessors[attributes.NORMAL];
    assert.equal(tangent.componentType, 5126);
    assert.equal(normal.componentType, 5126);
    const tView = doc.bufferViews[tangent.bufferView];
    const nView = doc.bufferViews[normal.bufferView];
    const tBase = (tView.byteOffset ?? 0) + (tangent.byteOffset ?? 0);
    const nBase = (nView.byteOffset ?? 0) + (normal.byteOffset ?? 0);
    for (let i = 0; i < tangent.count; i++) {
      const t = tBase + i * (tView.byteStride ?? 16);
      const n = nBase + i * (nView.byteStride ?? 12);
      const current = [0, 4, 8].map(offset => binary.readFloatLE(t + offset));
      const magnitude = Math.hypot(...current);
      if (magnitude > 1e-7) continue;
      // A clipped edge can inherit a collapsed UV derivative. A fallback
      // perpendicular to the normal preserves a valid shading basis.
      const [x, y, z] = [0, 4, 8].map(offset => binary.readFloatLE(n + offset));
      const perpendicular = Math.abs(z) < .9 ? [-y, x, 0] : [0, -z, y];
      const length = Math.hypot(...perpendicular);
      assert.ok(length > 1e-7);
      perpendicular.forEach((value, j) => binary.writeFloatLE(value / length, t + j * 4));
      fixed++;
    }
  }
  return fixed;
}

function skeleton(doc, binary) {
  const [skin] = doc.skins;
  assert.equal(skin.joints.length, 65);
  const names = new Map(skin.joints.map(index => [index, doc.nodes[index].name]));
  const accessor = doc.accessors[skin.inverseBindMatrices];
  const view = doc.bufferViews[accessor.bufferView];
  const base = (view.byteOffset ?? 0) + (accessor.byteOffset ?? 0);
  return new Map(skin.joints.map((joint, index) => [
    names.get(joint),
    {
      children: (doc.nodes[joint].children ?? []).filter(child => names.has(child)).map(child => names.get(child)).sort(),
      bind: Array.from({ length: 16 }, (_, element) =>
        binary.readFloatLE(base + index * (view.byteStride ?? 64) + element * 4)),
    },
  ]));
}

function imageSize(bytes, mime) {
  if (mime === 'image/png') return [bytes.readUInt32BE(16), bytes.readUInt32BE(20)];
  assert.equal(mime, 'image/jpeg');
  for (let i = 2; i < bytes.length && bytes[i] === 0xff; i += 2 + bytes.readUInt16BE(i + 2)) {
    if ([0xc0, 0xc1, 0xc2, 0xc3].includes(bytes[i + 1])) {
      return [bytes.readUInt16BE(i + 7), bytes.readUInt16BE(i + 5)];
    }
  }
  throw Error('Unknown JPEG frame header');
}

const motion = unpack(read('../round2/motion_male_fixed.glb'));
const expected = skeleton(motion.doc, motion.binary);
const results = {};

for (const key of releaseKeys) {
  const file = `male-${key}-v3.glb`;
  const orig = read(file);
  const bytes = sceneRoot(orig);
  const repairedTangents = repairDegenerateTangents(bytes);
  if (bytes !== orig || repairedTangents) {
    const stage = new URL(`qa/${key}-rooted.tmp`, root);
    writeFileSync(stage, bytes);
    renameSync(stage, new URL(file, root));
    const fitFile = new URL(`qa/fit-${key}.json`, root);
    const fit = JSON.parse(readFileSync(fitFile, 'utf8'));
    fit.sha256 = sha256(bytes);
    writeFileSync(fitFile, JSON.stringify(fit, null, 2) + '\n');
  }
  const { doc, binary } = unpack(bytes);
  const actual = skeleton(doc, binary);
  assert.equal(doc.animations, undefined);
  assert.equal(doc.nodes.filter(node => node.skin !== undefined).length, 1);
  const inverseBindMatrixMaxDifference = Math.max(...[...expected].flatMap(([name, joint]) => {
    const current = actual.get(name);
    assert.deepEqual(current.children, joint.children, name);
    return joint.bind.map((number, i) => Math.abs(number - current.bind[i]));
  }));
  const triangles = doc.meshes.flatMap(mesh => mesh.primitives)
    .reduce((count, primitive) => count + doc.accessors[primitive.indices].count / 3, 0);
  const images = (doc.images ?? []).map(image => {
    const view = doc.bufferViews[image.bufferView];
    const start = view.byteOffset ?? 0;
    return imageSize(binary.subarray(start, start + view.byteLength), image.mimeType);
  });
  const { issues } = await validator.validateBytes(new Uint8Array(bytes), { uri: file, maxIssues: 10000 });
  results[file] = {
    sha256: sha256(bytes), bytes: bytes.length, triangles, images, joints: actual.size,
    inverseBindMatrixMaxDifference, repairedTangents, errors: issues.numErrors, warnings: issues.numWarnings,
    messages: issues.messages,
  };
  console.log(file, bytes.length, triangles, images, issues.numErrors, issues.numWarnings);
}
writeFileSync(new URL('qa/gltf_validation.json', root), JSON.stringify(results, null, 2) + '\n');
for (const result of Object.values(results)) {
  assert.ok(result.bytes <= 1.5 * 1048576);
  assert.ok(result.triangles <= 6000);
  assert.ok(result.images.every(size => Math.max(...size) <= 1024));
  assert.ok(result.inverseBindMatrixMaxDifference < 5e-6);
  assert.equal(result.errors, 0);
  assert.equal(result.warnings, 0);
}

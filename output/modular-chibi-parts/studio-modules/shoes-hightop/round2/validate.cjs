const assert = require('node:assert/strict');
const crypto = require('node:crypto');
const fs = require('node:fs');
const path = require('node:path');
const validator = require('gltf-validator');

const here = __dirname;
const asset = path.join(here, 'shoes_hightop_v2.glb');
const source = path.join(here, '..', 'shoes_hightop_v1.glb');
const sha = bytes => crypto.createHash('sha256').update(bytes).digest('hex');
const write = (name, data) =>
  fs.writeFileSync(path.join(here, name), JSON.stringify(data, null, 2) + '\n');

function readGlb(bytes) {
  const length = bytes.readUInt32LE(12);
  const doc = JSON.parse(bytes.subarray(20, 20 + length));
  const binary = bytes.subarray(28 + length);
  const readView = index => {
    const view = doc.bufferViews[index];
    return binary.subarray(view.byteOffset, view.byteOffset + view.byteLength);
  };
  const readAccessor = index => readView(doc.accessors[index].bufferView);
  return {doc, readView, readAccessor};
}

function jpegSize(bytes) {
  assert.equal(bytes.readUInt16BE(0), 0xffd8);
  for (let offset = 2; offset + 9 < bytes.length;) {
    assert.equal(bytes[offset], 0xff);
    const marker = bytes[offset + 1];
    const length = bytes.readUInt16BE(offset + 2);
    if ([0xc0, 0xc1, 0xc2].includes(marker)) {
      const sampling = [];
      for (let component = 0; component < bytes[offset + 9]; component++) {
        sampling.push(bytes[offset + 11 + component * 3].toString(16));
      }
      return {width: bytes.readUInt16BE(offset + 7), height: bytes.readUInt16BE(offset + 5), sampling};
    }
    offset += 2 + length;
  }
  throw new Error('JPEG dimensions unavailable');
}

function contract(bytes) {
  const {doc, readView, readAccessor} = readGlb(bytes);
  const original = readGlb(fs.readFileSync(source));
  assert.equal(doc.meshes.length, 1);
  assert.equal(doc.skins.length, 1);
  const meshNodes = doc.nodes.filter(node => node.mesh !== undefined);
  assert.equal(meshNodes.length, 1);
  assert.equal(meshNodes[0].skin, 0);
  for (const field of ['animations', 'cameras']) assert.equal(doc[field]?.length ?? 0, 0);
  assert.equal(doc.extensions?.KHR_lights_punctual, undefined);
  const skin = doc.skins[0];
  assert.equal(skin.joints.length, 65);
  const jointNames = skin.joints.map(i => doc.nodes[i].name);
  assert.deepEqual(jointNames, original.doc.skins[0].joints.map(i => original.doc.nodes[i].name));
  assert(readAccessor(skin.inverseBindMatrices).equals(
    original.readAccessor(original.doc.skins[0].inverseBindMatrices)));
  const primitive = doc.meshes[0].primitives[0];
  const sourcePrimitive = original.doc.meshes[0].primitives[0];
  assert.equal(primitive.mode ?? 4, 4);
  const triangles = doc.accessors[primitive.indices].count / 3;
  assert(Number.isInteger(triangles) && triangles <= 3500);
  assert(readAccessor(primitive.indices).equals(original.readAccessor(sourcePrimitive.indices)));
  for (const key of ['TEXCOORD_0', 'NORMAL', 'TANGENT']) {
    assert(readAccessor(primitive.attributes[key]).equals(
      original.readAccessor(sourcePrimitive.attributes[key])));
  }
  assert.deepEqual(doc.materials, original.doc.materials);
  assert.equal(primitive.attributes.JOINTS_1, undefined);
  assert.equal(primitive.attributes.WEIGHTS_1, undefined);
  const weight = readAccessor(primitive.attributes.WEIGHTS_0);
  const joints = readAccessor(primitive.attributes.JOINTS_0);
  let maxInfluences = 0;
  for (let i = 0; i < joints.length; i += 4) {
    const values = Array.from({length: 4}, (_, slot) => weight.readFloatLE(4 * (i + slot)));
    assert(values.every((w, slot) => w >= 0 && joints[i + slot] < 65));
    assert(Math.abs(values.reduce((sum, w) => sum + w, 0) - 1) < .00001);
    maxInfluences = Math.max(maxInfluences, values.filter(w => w > 0).length);
  }
  assert(maxInfluences <= 4);

  const textures = doc.images.map(image => {
    const data = readView(image.bufferView);
    const {width, height, sampling} = jpegSize(data);
    assert(width <= 1024 && height <= 1024);
    assert.equal(image.mimeType, 'image/jpeg');
    return {name: image.name, width, height, sampling, bytes: data.length};
  });
  assert.equal(textures.length, 3);
  assert(bytes.length <= 1.2 * 1024 ** 2);

  return {
    exportSha256: sha(bytes), triangles, skinnedMeshes: meshNodes.length,
    joints: skin.joints.length, maxInfluences, embeddedAnimations: 0, textures, bytes: bytes.length,
    jointOrderMatchesV1: true, inverseBindBytesMatchV1: true,
    indexUvNormalTangentBytesMatchV1: true, materialsMatchV1: true,
    blendBytes: fs.statSync(asset.replace(/\.glb$/, '.blend')).size,
  };
}

async function main() {
  const bytes = fs.readFileSync(asset);
  const report = await validator.validateBytes(new Uint8Array(bytes), {
    uri: path.basename(asset),
    maxIssues: 2000,
  });
  report.exportSha256 = sha(bytes);
  write('validator.json', report);
  assert.equal(report.issues.numErrors, 0);
  assert.equal(report.issues.numWarnings, 0);
  const stats = contract(bytes);
  write('asset_contract.json', stats);
  console.log(JSON.stringify(stats, null, 2));
}

main().catch(error => {
  console.error(error);
  process.exitCode = 1;
});

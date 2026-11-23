'use strict';

const assert = require('node:assert/strict');
const crypto = require('node:crypto');
const fs = require('node:fs');
const path = require('node:path');
const validator = require('../../../../../node_modules/gltf-validator');

const inputPath = path.join(__dirname, '../shoes_sandals_v1.glb');
const exportName = 'shoes_sandals_v2.glb';
const maxBytes = Math.floor(1.2 * 1024 * 1024);
const sha256 = data => crypto.createHash('sha256').update(data).digest('hex');

function readGlb(filename) {
  const data = fs.readFileSync(filename);
  const jsonLength = data.readUInt32LE(12);
  assert.equal(data.toString('ascii', 0, 4), 'glTF');
  assert.equal(data.readUInt32LE(8), data.length);
  assert.equal(data.readUInt32LE(20 + jsonLength), data.length - 28 - jsonLength);
  const doc = JSON.parse(data.toString('utf8', 20, 20 + jsonLength));
  const bin = data.subarray(28 + jsonLength);

  function bufferView(index) {
    const view = doc.bufferViews[index];
    assert.equal(view.buffer, 0);
    return bin.subarray(view.byteOffset ?? 0, (view.byteOffset ?? 0) + view.byteLength);
  }

  function accessor(index) {
    const accessor = doc.accessors[index];
    const view = doc.bufferViews[accessor.bufferView];
    const widths = { SCALAR: 1, VEC2: 2, VEC3: 3, VEC4: 4, MAT4: 16 };
    const types = {
      5121: [1, 'readUInt8'],
      5123: [2, 'readUInt16LE'],
      5125: [4, 'readUInt32LE'],
      5126: [4, 'readFloatLE']
    };
    const width = widths[accessor.type];
    const [component, reader] = types[accessor.componentType];
    const stride = view.byteStride ?? width * component;
    const data = bufferView(accessor.bufferView);
    const base = accessor.byteOffset ?? 0;
    const at = (i, j) => data[reader](base + i * stride + j * component);
    return { at, count: accessor.count, width };
  }

  return { data, doc, bufferView, accessor };
}

function imageDimensions(bytes, mime) {
  if (mime === 'image/png') {
    assert.equal(bytes.toString('ascii', 12, 16), 'IHDR');
    return [bytes.readUInt32BE(16), bytes.readUInt32BE(20)];
  }
  assert.equal(mime, 'image/jpeg');
  assert.equal(bytes.readUInt16BE(0), 0xffd8);
  for (let offset = 2; offset < bytes.length;) {
    assert.equal(bytes[offset], 0xff);
    const marker = bytes[offset + 1];
    if ([0xc0, 0xc1, 0xc2, 0xc3].includes(marker)) {
      return [bytes.readUInt16BE(offset + 7), bytes.readUInt16BE(offset + 5)];
    }
    offset += 2 + bytes.readUInt16BE(offset + 2);
  }
  throw new Error('Missing JPEG start of frame');
}

function textureData(asset) {
  const material = asset.doc.materials[0];
  const slots = {
    base_color: material.pbrMetallicRoughness.baseColorTexture.index,
    normal: material.normalTexture.index,
    metallic_roughness: material.pbrMetallicRoughness.metallicRoughnessTexture.index
  };
  return Object.fromEntries(Object.entries(slots).map(([role, id]) => {
    const image = asset.doc.images[asset.doc.textures[id].source];
    const bytes = asset.bufferView(image.bufferView);
    const size = imageDimensions(bytes, image.mimeType);
    return [role, { size_px: size, mime_type: image.mimeType, bytes: bytes.length, sha256: sha256(bytes) }];
  }));
}

function skinData({ doc, accessor }) {
  assert.equal(doc.skins.length, 1);
  const skin = doc.skins[0];
  const matrices = accessor(skin.inverseBindMatrices);
  return {
    joints: skin.joints.map(index => doc.nodes[index].name),
    inverse_bind_matrices: Array.from({ length: matrices.count }, (_, i) =>
      Array.from({ length: matrices.width }, (_, j) => matrices.at(i, j)))
  };
}

async function main() {
  const initial = readGlb(inputPath);
  const asset = readGlb(path.join(__dirname, exportName));
  const { data, doc, accessor } = asset;
  const validatorReport = await validator.validateBytes(new Uint8Array(data), { uri: exportName, maxIssues: 0 });
  fs.writeFileSync(path.join(__dirname, 'validator.json'), JSON.stringify(validatorReport, null, 2) + '\n');
  assert.equal(validatorReport.issues.numErrors, 0);
  assert.equal(validatorReport.issues.numWarnings, 0);
  assert.ok(data.length <= maxBytes, `${data.length} bytes exceeds ${maxBytes}`);

  assert.equal(doc.meshes.length, 1);
  assert.equal(doc.nodes.filter(node => node.mesh !== undefined && node.skin === 0).length, 1);
  assert.equal(doc.nodes.length, 66);
  assert.equal(doc.animations?.length ?? 0, 0);
  assert.equal(doc.cameras?.length ?? 0, 0);
  assert.deepEqual(doc.materials, initial.doc.materials);
  const skin = skinData(asset);
  assert.equal(skin.joints.length, 65);
  assert.deepEqual(skin, skinData(initial));

  const textures = textureData(asset);
  assert.equal(doc.images.length, 3);
  for (const texture of Object.values(textures)) assert.ok(Math.max(...texture.size_px) <= 1024);
  assert.deepEqual(textures.base_color, textureData(initial).base_color);

  let maxInfluences = 0;
  let triangles = 0;
  let maxCornerDisplacement = 0;
  let changedCorners = 0;
  const primitives = doc.meshes[0].primitives;
  for (const [p, primitive] of primitives.entries()) {
    const attributes = primitive.attributes;
    const weights = accessor(attributes.WEIGHTS_0);
    const joints = accessor(attributes.JOINTS_0);
    const position = accessor(attributes.POSITION);
    const uv = accessor(attributes.TEXCOORD_0);
    const indices = accessor(primitive.indices);
    assert.equal(attributes.WEIGHTS_1, undefined);
    assert.equal(attributes.JOINTS_1, undefined);
    assert.equal(primitive.mode ?? 4, 4);
    assert.equal(indices.count % 3, 0);
    for (let i = 0; i < weights.count; i++) {
      let sum = 0;
      let active = 0;
      const side = position.at(i, 0) > 0 ? 'Left' : 'Right';
      for (let j = 0; j < weights.width; j++) {
        const weight = weights.at(i, j);
        sum += weight;
        if (weight > 0) {
          active++;
          assert.ok(skin.joints[joints.at(i, j)].startsWith(`mixamorig:${side}`));
        }
      }
      assert.ok(Math.abs(sum - 1) < 1e-5 && active > 0);
      maxInfluences = Math.max(active, maxInfluences);
    }
    const original = initial.doc.meshes[0].primitives[p];
    const originalIndices = initial.accessor(original.indices);
    const originalPosition = initial.accessor(original.attributes.POSITION);
    const originalUv = initial.accessor(original.attributes.TEXCOORD_0);
    assert.equal(indices.count, originalIndices.count);
    for (let i = 0; i < indices.count; i++) {
      const previous = originalIndices.at(i, 0);
      const current = indices.at(i, 0);
      for (let axis = 0; axis < 2; axis++) assert.ok(Math.abs(uv.at(current, axis) - originalUv.at(previous, axis)) < 1e-7);
      const displacement = Math.hypot(...[0, 1, 2].map(axis => position.at(current, axis) - originalPosition.at(previous, axis)));
      maxCornerDisplacement = Math.max(displacement, maxCornerDisplacement);
      changedCorners += Number(displacement > 1e-6);
    }
    triangles += indices.count / 3;
  }
  assert.ok(triangles <= 3500 && maxInfluences <= 4 && maxCornerDisplacement <= 0.020001);
  const blend = fs.readFileSync(path.join(__dirname, 'shoes_sandals_v2.blend'));
  const report = {
    glb_sha256: sha256(data), glb_bytes: data.length, glb_limit_bytes: maxBytes,
    blend_sha256: sha256(blend), blend_bytes: blend.length,
    original_glb_bytes: initial.data.length, triangles, mesh_count: doc.meshes.length, animations: 0,
    joints: skin.joints.length, maximum_influences: maxInfluences,
    joint_order_and_inverse_bind_matrices_identical: true, material_settings_and_uvs_match_v1: true,
    moved_triangle_corners: changedCorners, maximum_corner_displacement_m: maxCornerDisplacement, textures,
    validator_errors: validatorReport.issues.numErrors, validator_warnings: validatorReport.issues.numWarnings
  };
  fs.writeFileSync(path.join(__dirname, 'asset_contract.json'), JSON.stringify(report, null, 2) + '\n');
  console.log(JSON.stringify(report, null, 2));
}

main().catch(error => {
  console.error(error);
  process.exitCode = 1;
});

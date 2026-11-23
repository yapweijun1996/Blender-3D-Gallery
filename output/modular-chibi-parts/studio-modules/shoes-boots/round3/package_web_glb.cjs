/* Repack the Blender export with its three high-quality JPEG atlases and verify the GLB. */
const assert = require('node:assert/strict');
const { createHash } = require('node:crypto');
const fs = require('node:fs');
const path = require('node:path');
const validator = require('gltf-validator');

const out = __dirname;
const target = path.join(out, 'shoes_boots_v3.glb');
const v2 = path.join(out, '..', 'round2', 'shoes_boots_v2.glb');
const raw = path.join(out, 'boots_export_raw.glb');
const sha = (data) => createHash('sha256').update(data).digest('hex');
const align4 = (size) => Math.ceil(size / 4) * 4;

function readGlb(file) {
  const bytes = fs.readFileSync(file);
  const jsonLength = bytes.readUInt32LE(12);
  assert.equal(bytes.toString('ascii', 0, 4), 'glTF');
  assert.equal(bytes.readUInt32LE(8), bytes.length);
  return {
    bytes,
    doc: JSON.parse(bytes.toString('utf8', 20, 20 + jsonLength)),
    bin: bytes.subarray(28 + jsonLength),
  };
}

function encodeGlb(doc, bin) {
  const json = Buffer.from(JSON.stringify(doc));
  const padded = Buffer.alloc(align4(json.length), 32);
  json.copy(padded);
  const header = Buffer.alloc(12);
  header.write('glTF');
  header.writeUInt32LE(2, 4);
  header.writeUInt32LE(header.length + 16 + padded.length + bin.length, 8);
  const jsonHeader = Buffer.alloc(8);
  jsonHeader.writeUInt32LE(padded.length);
  jsonHeader.write('JSON', 4);
  const binHeader = Buffer.alloc(8);
  binHeader.writeUInt32LE(bin.length);
  binHeader.write('BIN\0', 4);
  return Buffer.concat([header, jsonHeader, padded, binHeader, bin]);
}

function repack() {
  const { doc, bin } = readGlb(raw);
  assert.equal(doc.buffers.length, 1);
  assert.equal(doc.images.length, 3);
  const images = new Map(doc.images.map((image) => [image.bufferView, image]));
  assert.equal(images.size, doc.images.length);
  const chunks = [];
  let length = 0;
  for (const [index, view] of doc.bufferViews.entries()) {
    assert.equal(view.buffer, 0);
    const image = images.get(index);
    const offset = view.byteOffset || 0;
    const source = image
      ? fs.readFileSync(path.join(out, `${image.name}.jpg`))
      : bin.subarray(offset, offset + view.byteLength);
    assert.equal(source.length > 0, true);
    if (image) {
      assert.equal(source.readUInt16BE(0), 0xffd8);
      image.mimeType = 'image/jpeg';
    }
    view.byteOffset = length;
    view.byteLength = source.length;
    chunks.push(source, Buffer.alloc(align4(source.length) - source.length));
    length += align4(source.length);
  }
  doc.buffers[0].byteLength = length;
  fs.writeFileSync(target, encodeGlb(doc, Buffer.concat(chunks)));
}

function accessorRows(glb, index) {
  const accessor = glb.doc.accessors[index];
  const view = glb.doc.bufferViews[accessor.bufferView];
  const components = { SCALAR: 1, VEC2: 2, VEC3: 3, VEC4: 4, MAT4: 16 }[accessor.type];
  const formats = {
    5121: [1, 'readUInt8', 255], 5123: [2, 'readUInt16LE', 65535],
    5125: [4, 'readUInt32LE', 4294967295], 5126: [4, 'readFloatLE', 1],
  };
  const [size, read, unit] = formats[accessor.componentType];
  const start = (view.byteOffset || 0) + (accessor.byteOffset || 0);
  const stride = view.byteStride || components * size;
  return Array.from({ length: accessor.count }, (_, row) =>
    Array.from({ length: components }, (_, col) =>
      glb.bin[read](start + stride * row + size * col) / (accessor.normalized ? unit : 1)));
}

async function verify() {
  const glb = readGlb(target);
  const source = readGlb(v2);
  const { doc, bytes } = glb;
  const uri = path.basename(target);
  const validation = await validator.validateBytes(bytes, { uri, maxIssues: 0 });
  validation.export_sha256 = sha(bytes);
  fs.writeFileSync(path.join(out, 'checks', 'khronos_validator.json'),
    JSON.stringify(validation, null, 2) + '\n');
  const [skin] = doc.skins;
  const jointNames = skin.joints.map((id) => doc.nodes[id].name);
  const sourceNames = source.doc.skins[0].joints.map((id) => source.doc.nodes[id].name);
  const beforeBinds = accessorRows(source, source.doc.skins[0].inverseBindMatrices);
  const afterBinds = accessorRows(glb, skin.inverseBindMatrices);
  const bindDelta = Math.max(...afterBinds.flatMap((row, i) =>
    row.map((value, j) => Math.abs(value - beforeBinds[i][j]))));
  const skinned = doc.nodes.filter((n) => n.mesh !== undefined);
  const primitive = doc.meshes[0].primitives[0];
  const positions = accessorRows(glb, primitive.attributes.POSITION);
  const tangents = accessorRows(glb, primitive.attributes.TANGENT);
  const joints = accessorRows(glb, primitive.attributes.JOINTS_0);
  const weights = accessorRows(glb, primitive.attributes.WEIGHTS_0);
  const tangentLengthError = Math.max(...tangents.map(([x, y, z]) => Math.abs(Math.hypot(x, y, z) - 1)));
  const triangles = doc.accessors[primitive.indices].count / 3;
  const sourceTriangles = source.doc.accessors[source.doc.meshes[0].primitives[0].indices].count / 3;
  const maxInfluences = Math.max(...weights.map((row) => row.filter((w) => w > 0).length));
  const weightError = Math.max(...weights.map((row) =>
    Math.abs(row.reduce((sum, value) => sum + value, 0) - 1)));
  const textures = validation.info.resources.filter((r) => r.image).map((r) => {
    const image = doc.images[Number(r.pointer.split('/').at(-1))];
    return {
      name: image.name, width: r.image.width, height: r.image.height, mime: r.mimeType,
      bytes: doc.bufferViews[image.bufferView].byteLength,
    };
  });
  const report = {
    export_sha256: sha(bytes), source_sha256: sha(source.bytes), bytes: bytes.length,
    source_bytes: source.bytes.length, blend_bytes: fs.statSync(target.replace('.glb', '.blend')).size,
    triangles, source_triangles: sourceTriangles, exported_vertices: positions.length,
    meshes: doc.meshes.length, skins: doc.skins.length, joints: jointNames.length,
    joint_names: jointNames, inverse_bind_max_abs_delta: bindDelta, max_influences: maxInfluences,
    max_weight_sum_error: weightError, max_tangent_length_error: tangentLengthError,
    animation_count: (doc.animations || []).length,
    camera_count: (doc.cameras || []).length,
    errors: validation.issues.numErrors, warnings: validation.issues.numWarnings,
    textures,
  };
  fs.writeFileSync(path.join(out, 'checks', 'asset_contract.json'),
    JSON.stringify(report, null, 2) + '\n');
  assert.equal(report.errors + report.warnings, 0);
  assert.ok(tangentLengthError < 1e-4 && tangents.every((row) => Math.abs(row[3]) === 1));
  assert.equal(report.meshes, 1);
  assert.equal(report.skins, 1);
  assert.equal(skinned.length, 1);
  assert.equal(skinned[0].skin, 0);
  assert.equal(doc.meshes[0].primitives.length, 1);
  assert.equal(primitive.mode ?? 4, 4);
  assert.equal(report.joints, 65);
  assert.deepEqual(jointNames, sourceNames);
  assert.ok(bindDelta < 1e-6);
  assert.equal(report.animation_count + report.camera_count, 0);
  assert.equal(doc.extensionsUsed?.includes('KHR_lights_punctual') ?? false, false);
  assert.ok(triangles <= 3500 && bytes.length <= 1.2 * 1024 ** 2);
  assert.equal(textures.length, 3);
  assert.ok(textures.every((r) => r.width <= 1024 && r.height <= 1024));
  assert.ok(doc.images.every((image) => image.bufferView !== undefined && !image.uri));
  assert.ok(!Object.keys(primitive.attributes).some((name) => /^(JOINTS|WEIGHTS)_[1-9]/.test(name)));
  assert.ok(maxInfluences <= 4 && weightError < 1e-5);
  assert.ok(joints.every((row) => row.every((joint) => joint >= 0 && joint < 65)));
  console.log(JSON.stringify({ bytes: bytes.length, triangles, maxInfluences, textures,
    errors: report.errors, warnings: report.warnings }));
}

fs.mkdirSync(path.join(out, 'checks'), { recursive: true });
if (!process.argv.includes('--verify-only')) repack();
verify().catch((error) => { console.error(error); process.exitCode = 1; });

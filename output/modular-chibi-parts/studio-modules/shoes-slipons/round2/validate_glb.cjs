const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const validator = require('gltf-validator');

const root = __dirname;
const qa = path.join(root, 'qa');
const name = 'shoes_slipons_v2.glb';
const hash = bytes => crypto.createHash('sha256').update(bytes).digest('hex');
const budget = Math.floor(1.2 * 1024 ** 2);
const load = file => {
  const bytes = fs.readFileSync(file);
  assert.equal(bytes.toString('ascii', 0, 4), 'glTF');
  assert.equal(bytes.readUInt32LE(8), bytes.length);
  const length = bytes.readUInt32LE(12);
  const doc = JSON.parse(bytes.toString('utf8', 20, 20 + length));
  const view = index => {
    const { byteOffset = 0, byteLength } = doc.bufferViews[index];
    const start = 28 + length + byteOffset;
    return bytes.subarray(start, start + byteLength);
  };
  const values = index => {
    const accessor = doc.accessors[index];
    const components = {SCALAR: 1, VEC2: 2, VEC3: 3, VEC4: 4, MAT4: 16}[accessor.type];
    const bytes = {5121: 1, 5123: 2, 5126: 4}[accessor.componentType];
    assert(!doc.bufferViews[accessor.bufferView].byteStride);
    const offset = accessor.byteOffset ?? 0;
    return view(accessor.bufferView).subarray(offset, offset + bytes * accessor.count * components);
  };
  return { bytes, doc, view, values };
};

function jpegSize(bytes) {
  assert.equal(bytes.readUInt16BE(0), 0xffd8);
  for (let i = 2; i < bytes.length && bytes[i] === 255; ) {
    if ([0xc0, 0xc1, 0xc2].includes(bytes[i+1])) {
      return { width: bytes.readUInt16BE(i+7), height: bytes.readUInt16BE(i+5) };
    }
    i += 2 + bytes.readUInt16BE(i+2);
  }
  throw new Error('Missing JPEG image dimensions');
}

async function main() {
  const model = load(path.join(root, name));
  const source = load(path.join(root, '..', 'shoes_slipons_v1.glb'));
  const master = load(path.join(root, '../../../master/base_body.glb'));
  const { doc } = model;
  const blend = fs.readFileSync(path.join(root, 'shoes_slipons_v2.blend'));
  assert(model.bytes.length <= budget);
  assert.equal(doc.meshes.length, 1);
  assert.equal(doc.skins.length, 1);
  assert.equal(doc.animations?.length ?? 0, 0);
  assert(!doc.cameras?.length && !doc.extensions?.KHR_lights_punctual);
  const joints = asset => asset.doc.skins[0].joints.map(i => asset.doc.nodes[i].name);
  assert.equal(joints(model).length, 65);
  assert.deepEqual(doc.nodes, source.doc.nodes);
  assert.deepEqual(doc.materials, source.doc.materials);
  assert.deepEqual(doc.textures, source.doc.textures);
  assert.deepEqual(joints(model), joints(master));
  assert.deepEqual(model.values(doc.skins[0].inverseBindMatrices),
                   master.values(master.doc.skins[0].inverseBindMatrices));
  assert(doc.nodes.every(n => n.mesh === 0 || joints(model).includes(n.name)));

  let triangles = 0;
  let activeInfluences = 0;
  let changed = 0;
  let maxDisplacementM = 0;
  const primitives = doc.meshes[0].primitives;
  assert.equal(primitives.length, source.doc.meshes[0].primitives.length);
  for (const [p, primitive] of primitives.entries()) {
    const a = primitive.attributes;
    const other = source.doc.meshes[0].primitives[p];
    assert.equal(primitive.mode ?? 4, 4);
    assert(a.WEIGHTS_0 !== undefined && a.JOINTS_0 !== undefined);
    assert(a.WEIGHTS_1 === undefined && a.JOINTS_1 === undefined);
    assert.equal(primitive.material, other.material);
    assert.deepEqual(model.values(a.TEXCOORD_0), source.values(other.attributes.TEXCOORD_0));
    assert.deepEqual(model.values(primitive.indices), source.values(other.indices));
    triangles += doc.accessors[primitive.indices].count / 3;
    const w = model.values(a.WEIGHTS_0);
    const j = model.values(a.JOINTS_0);
    const p1 = source.values(other.attributes.POSITION);
    const p2 = model.values(a.POSITION);
    for (let i = 0; i < doc.accessors[a.POSITION].count; i++) {
      const shift = Math.hypot(...[0, 4, 8].map(k => p2.readFloatLE(i * 12 + k) - p1.readFloatLE(i * 12 + k)));
      changed += Number(shift > 1e-9);
      maxDisplacementM = Math.max(maxDisplacementM, shift);
      const weights = Array.from({ length: 4 }, (_, k) => w.readFloatLE(i * 16 + 4 * k));
      const sum = weights.reduce((a, b) => a + b, 0);
      const active = weights.flatMap((w, k) => w > 0 ? [j[i * 4 + k]] : []);
      assert(Math.abs(sum - 1) <= 1e-5);
      const side = p2.readFloatLE(i * 12) > 0 ? 'Left' : 'Right';
      assert(active.every(index => ['Leg', 'Foot', 'ToeBase'].some(joint =>
        joints(model)[index] === `mixamorig:${side}${joint}`)));
      activeInfluences = Math.max(activeInfluences, active.length);
    }
  }
  assert(triangles <= 3500 && maxDisplacementM <= .02);
  const textures = doc.images.map(image => {
    assert(!image.uri && image.bufferView !== undefined);
    const data = model.view(image.bufferView);
    const size = image.mimeType === 'image/jpeg' ? jpegSize(data) : {
      width: data.readUInt32BE(16), height: data.readUInt32BE(20),
    };
    assert(Math.max(size.width, size.height) <= 1024);
    return { name: image.name, ...size, bytes: data.length, mime_type: image.mimeType };
  });

  fs.mkdirSync(qa, { recursive: true });
  const result = await validator.validateBytes(model.bytes, { uri: name, format: 'glb', maxIssues: 0 });
  result.glb_sha256 = hash(model.bytes);
  fs.writeFileSync(path.join(qa, 'validator.json'), JSON.stringify(result, null, 2) + '\n');
  console.log(result.issues);
  assert.equal(result.issues.numErrors, 0);
  assert.equal(result.issues.numWarnings, 0);
  const contract = {
    glb_sha256: result.glb_sha256, blend_sha256: hash(blend), source_glb_sha256: hash(source.bytes),
    glb_bytes: model.bytes.length, source_glb_bytes: source.bytes.length, glb_byte_limit: budget,
    blend_bytes: blend.length, triangles, meshes: 1, primitives: primitives.length, skins: 1,
    joints: joints(model).length, animations: 0, max_active_influences: activeInfluences,
    original_topology_uvs_materials_and_joint_order_preserved: true,
    inverse_binds_match_master_export: true, moved_export_vertices: changed,
    max_displacement_m: maxDisplacementM, embedded_textures: textures,
    validator_version: result.validatorVersion,
  };
  fs.writeFileSync(path.join(qa, 'asset_contract.json'), JSON.stringify(contract, null, 2) + '\n');
  console.log(contract);
}

main().catch(err => {
  console.error(err);
  process.exitCode = 1;
});

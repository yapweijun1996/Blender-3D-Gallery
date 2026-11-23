const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const { createHash } = require('node:crypto');
const validator = require('../../../../../node_modules/gltf-validator');

const here = __dirname;
const parts = path.resolve(here, '../../..');
const target = path.join(here, 'shorts_v1.glb');
const raw = fs.readFileSync(target);
const sha = (bytes) => createHash('sha256').update(bytes).digest('hex');
const write = (name, data) => fs.writeFileSync(path.join(here, name), JSON.stringify(data, null, 2) + '\n');

function decode(bytes) {
  const size = bytes.readUInt32LE(12);
  const doc = JSON.parse(bytes.toString('utf8', 20, 20 + size));
  const bin = bytes.subarray(28 + size);
  function view(index) {
    const spec = doc.bufferViews[index];
    const offset = spec.byteOffset ?? 0;
    return bin.subarray(offset, offset + spec.byteLength);
  }
  function rows(index) {
    const spec = doc.accessors[index];
    const types = {
      5121: ['readUInt8', 1], 5123: ['readUInt16LE', 2], 5125: ['readUInt32LE', 4], 5126: ['readFloatLE', 4],
    };
    const [method, width] = types[spec.componentType];
    const size = { SCALAR: 1, VEC2: 2, VEC3: 3, VEC4: 4 }[spec.type];
    const stride = doc.bufferViews[spec.bufferView].byteStride ?? width * size;
    const buffer = view(spec.bufferView);
    return Array.from({ length: spec.count }, (_, row) => Array.from({ length: size },
      (_, column) => buffer[method]((spec.byteOffset ?? 0) + row * stride + column * width)));
  }
  return { doc, view, rows };
}

function texture(model, mesh) {
  const material = model.doc.materials[mesh.primitives[0].material];
  const sampler = model.doc.textures[material.pbrMetallicRoughness.baseColorTexture.index];
  return model.view(model.doc.images[sampler.source].bufferView);
}

async function main() {
  const report = await validator.validateBytes(new Uint8Array(raw), {
    uri: 'shorts_v1.glb', maxIssues: 0, writeTimestamp: false,
  });
  report.glb_sha256 = sha(raw);
  write('gltf_validator.json', report);
  const model = decode(raw);
  const { doc, rows } = model;
  const [mesh] = doc.meshes;
  const [primitive] = mesh.primitives;
  const [skin] = doc.skins;
  const indices = rows(primitive.indices).flat();
  const position = rows(primitive.attributes.POSITION);
  const weights = rows(primitive.attributes.WEIGHTS_0);
  const uv = rows(primitive.attributes.TEXCOORD_0);
  const joints = skin.joints.map((node) => doc.nodes[node].name);
  const master = decode(fs.readFileSync(path.join(parts, 'master/base_body.glb'))).doc;
  const masterJoints = master.skins[0].joints.map((node) => master.nodes[node].name);
  const source = decode(fs.readFileSync(path.join(here, '../source_studio_segmented.glb')));
  const sourceNode = source.doc.nodes.find((node) => node.name === 'tripo_part_5');
  const sourceMesh = source.doc.meshes[sourceNode.mesh];
  const exactBaseColor = texture(source, sourceMesh).equals(texture(model, mesh));
  const weld = new Map();
  const vertices = position.map((p) => {
    const key = p.join(',');
    if (!weld.has(key)) weld.set(key, weld.size);
    return weld.get(key);
  });
  const edges = new Map();
  const linked = Array.from({ length: weld.size }, () => []);
  let degenerates = 0;
  for (let i = 0; i < indices.length; i += 3) {
    const tri = indices.slice(i, i + 3).map((index) => vertices[index]);
    if (new Set(tri).size < 3) degenerates++;
    for (let edge = 0; edge < 3; edge++) {
      const a = tri[edge], b = tri[(edge + 1) % 3];
      const key = Math.min(a, b) * weld.size + Math.max(a, b);
      const entry = edges.get(key) ?? [0, 0];
      entry[0]++;
      entry[1] += Math.sign(b - a);
      edges.set(key, entry);
      linked[a].push(b);
      linked[b].push(a);
    }
  }
  let connectedComponents = 0;
  const seen = new Set();
  for (let v = 0; v < weld.size; v++) {
    if (seen.has(v)) continue;
    connectedComponents++;
    seen.add(v);
    const pending = [v];
    while (pending.length) for (const other of linked[pending.pop()]) {
      if (!seen.has(other)) {
        seen.add(other);
        pending.push(other);
      }
    }
  }
  const maxInfluences = Math.max(...weights.map((values) => values.filter((n) => n > 0).length));
  const maxWeightSumError = Math.max(...weights.map((values) => Math.abs(values.reduce((a, b) => a + b) - 1)));
  const boundaryEdges = [...edges.values()].filter(([count]) => count === 1).length;
  const nonManifoldEdges = [...edges.values()].filter(([count]) => count !== 2).length;
  const unbalancedWinding = [...edges.values()].filter(([, direction]) => direction).length;
  const textures = report.info.resources.filter((resource) => resource.image).map((resource) => resource.image);
  const results = {
    glb_sha256: sha(raw), bytes: raw.length, triangles: indices.length / 3, exported_vertices: position.length,
    welded_vertices: weld.size, welded_edges: edges.size, boundary_edges: boundaryEdges,
    non_manifold_edges: nonManifoldEdges, connected_components: connectedComponents,
    unbalanced_edges: unbalancedWinding, degenerate_faces: degenerates, textures,
    tripo_base_color_bytes_equal: exactBaseColor, tripo_base_color_sha256: sha(texture(model, mesh)),
    texcoord0_finite: uv.flat().every(Number.isFinite), max_influences: maxInfluences,
    max_weight_sum_error: maxWeightSumError, joints, identical_master_joint_order: joints.join() === masterJoints.join(),
    identical_master_joint_set: [...joints].sort().join() === [...masterJoints].sort().join(),
    meshes: doc.meshes.length, primitives: mesh.primitives.length, skins: doc.skins.length,
    animations: (doc.animations ?? []).length,
  };
  write('export_check.json', results);
  assert.equal(report.issues.numErrors + report.issues.numWarnings, 0);
  assert.ok(results.triangles <= 3000 && raw.length <= 1.2 * 1024 ** 2);
  assert.ok(connectedComponents === 1 && !boundaryEdges && !nonManifoldEdges && !degenerates && !unbalancedWinding);
  assert.ok(joints.length === 65 && results.identical_master_joint_set);
  assert.ok(maxWeightSumError < 1e-5 && maxInfluences <= 4 && primitive.attributes.JOINTS_1 === undefined);
  assert.ok(exactBaseColor && results.texcoord0_finite);
  assert.ok(textures.length && textures.every(({ width, height }) => Math.max(width, height) <= 1024));
  assert.ok(results.meshes === 1 && results.primitives === 1 && results.skins === 1 && results.animations === 0);
  console.log(JSON.stringify({ triangles: results.triangles, bytes: results.bytes,
    joints: joints.length, maxInfluences, khronos: report.issues }, null, 2));
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});

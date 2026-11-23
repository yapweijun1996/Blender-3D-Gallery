/* Validate the delivered GLBs and measure the bytes the game will load. */
const assert = require('node:assert/strict');
const { createHash } = require('node:crypto');
const { readFileSync, writeFileSync } = require('node:fs');
const { join } = require('node:path');
const validator = require('gltf-validator');

const models = {
  rain_tree: [1800, [18, 14, 15.2]],
  angsana: [1500, [12.8, 15.5, 11.7]],
  tembusu: [1500, [10, 15, 9.3]],
  royal_palm: [1100, [5, 17, 4.8]],
  coconut_palm: [900, [6.3, 12.5, 5.6]],
  bottle_palm: [700, [3.6, 4.3, 3.3]],
  frangipani: [700, [4.5, 4.2, 3.8]],
  bougainvillea: [600, [2.75, 1.42, 2.1]],
  heliconia: [500, [1.65, 1.8, 1.35]],
  ginger: [400, [1.4, 1.64, 1.15]],
  hedge_2m: [150, [2, .96, .72]],
  grass_tuft: [80, [.33, .27, .31]],
  flower_bed: [400, [2, .42, 1]],
  planter_box: [200, [1.55, .68, .65]],
  tree_pit: [200, [1.6, .09, 1.6]],
};
const allowedMaterials = new Set([
  'paint', 'glass', 'window', 'wall', 'roof', 'concrete', 'metal', 'chrome',
  'trim', 'stone', 'water', 'leaf', 'trunk', 'light', 'lamp_emissive',
  'rubber', 'plate',
]);

function sha256(bytes) {
  return createHash('sha256').update(bytes).digest('hex');
}

function readGlb(bytes) {
  assert.equal(bytes.readUInt32LE(0), 0x46546c67);
  assert.equal(bytes.readUInt32LE(4), 2);
  assert.equal(bytes.readUInt32LE(8), bytes.length);
  const end = 20 + bytes.readUInt32LE(12);
  assert.equal(bytes.readUInt32LE(16), 0x4e4f534a);
  assert.equal(bytes.readUInt32LE(end + 4), 0x004e4942);
  return [JSON.parse(bytes.subarray(20, end)), bytes.subarray(end + 8)];
}

function readPositions(accessor, doc, binary) {
  assert.equal(accessor.componentType, 5126);
  assert.equal(accessor.type, 'VEC3');
  const view = doc.bufferViews[accessor.bufferView];
  const offset = (view.byteOffset || 0) + (accessor.byteOffset || 0);
  return Array.from({ length: accessor.count }, (_, i) => {
    const ptr = offset + i * (view.byteStride || 12);
    return [0, 4, 8].map(delta => binary.readFloatLE(ptr + delta));
  });
}

function readIndices(accessor, doc, binary) {
  const view = doc.bufferViews[accessor.bufferView];
  const offset = (view.byteOffset || 0) + (accessor.byteOffset || 0);
  const sizes = { 5121: 1, 5123: 2, 5125: 4 };
  const size = sizes[accessor.componentType];
  assert(size);
  return Array.from({ length: accessor.count }, (_, i) => binary.readUIntLE(offset + i * size, size));
}

function measure(doc, binary, root, expectedSize) {
  assert(root.children?.length);
  const parts = [];
  const min = [Infinity, Infinity, Infinity];
  const max = [-Infinity, -Infinity, -Infinity];
  for (const nodeIndex of root.children) {
    const node = doc.nodes[nodeIndex];
    assert(node.name.startsWith(root.name + '_'));
    assert.equal(node.children, undefined);
    for (const target of [node, root]) {
      assert(!target.matrix && !target.translation && !target.rotation && !target.scale);
    }
    const mesh = doc.meshes[node.mesh];
    let triangles = 0;
    for (const primitive of mesh.primitives) {
      assert.equal(primitive.mode ?? 4, 4);
      assert(primitive.attributes.COLOR_0 !== undefined);
      assert.equal(doc.accessors[primitive.attributes.COLOR_0].type, 'VEC3');
      const positions = readPositions(doc.accessors[primitive.attributes.POSITION], doc, binary);
      const indices = readIndices(doc.accessors[primitive.indices], doc, binary);
      assert(indices.length % 3 === 0);
      for (let i = 0; i < indices.length; i += 3) {
        const [a, b, c] = indices.slice(i, i + 3).map(index => positions[index]);
        const u = b.map((coord, axis) => coord - a[axis]);
        const v = c.map((coord, axis) => coord - a[axis]);
        const cross = u.map((_, axis) => u[(axis + 1) % 3] * v[(axis + 2) % 3] - u[(axis + 2) % 3] * v[(axis + 1) % 3]);
        assert(Math.hypot(...cross) > 1e-10, `Degenerate triangle in ${node.name}`);
      }
      for (const p of positions) {
        for (let axis = 0; axis < 3; axis++) {
          min[axis] = Math.min(min[axis], p[axis]);
          max[axis] = Math.max(max[axis], p[axis]);
        }
      }
      triangles += indices.length / 3;
    }
    parts.push({ name: node.name, triangles });
  }
  const size = max.map((bound, axis) => bound - min[axis]);
  size.forEach((extent, axis) => assert(Math.abs(extent - expectedSize[axis]) < 1e-5));
  assert(Math.abs(min[1]) < 1e-6, `${root.name} ground plane`);
  assert(min[0] < 0 && max[0] > 0 && min[2] < 0 && max[2] > 0);
  const rounded = values => values.map(value => Number(value.toFixed(5)));
  return {
    triangles: parts.reduce((total, part) => total + part.triangles, 0),
    parts,
    bounds_metres: { min: rounded(min), max: rounded(max) },
    size_metres: rounded(size),
  };
}

async function main() {
  const results = [];
  for (const [slug, [budget, expectedSize]] of Object.entries(models)) {
    const file = slug + '.glb';
    const bytes = readFileSync(join(__dirname, file));
    try {
      assert(bytes.length <= 1.8 * 1024 * 1024);
      const report = await validator.validateBytes(new Uint8Array(bytes), { uri: file, maxIssues: 0 });
      assert(report.issues.numErrors === 0 && report.issues.numWarnings === 0,
        JSON.stringify(report.issues.messages));
      const [doc, binary] = readGlb(bytes);
      assert.equal(doc.buffers.length, 1);
      assert.equal(doc.buffers[0].uri, undefined);
      for (const key of ['textures', 'images', 'animations', 'skins', 'cameras', 'extensionsRequired', 'extensions']) {
        assert(!doc[key]?.length && (!doc[key] || Object.keys(doc[key]).length === 0), key);
      }
      const materials = doc.materials.map(material => {
        assert(allowedMaterials.has(material.name), material.name);
        assert.equal(material.alphaMode ?? 'OPAQUE', 'OPAQUE');
        return material.name;
      });
      assert.equal(new Set(materials).size, materials.length);
      const roots = Object.fromEntries(doc.scenes[doc.scene ?? 0].nodes.map(index => {
        const node = doc.nodes[index];
        return [node.name, node];
      }));
      assert.deepEqual(Object.keys(roots).sort(), ['lod0', 'lod1']);
      const lods = {};
      for (const lod of ['lod0', 'lod1']) {
        assert.equal(roots[lod].extras.lod_level, Number(lod.at(-1)));
        lods[lod] = measure(doc, binary, roots[lod], expectedSize);
      }
      assert.equal(doc.nodes.length, 2 + lods.lod0.parts.length + lods.lod1.parts.length);
      assert(lods.lod0.triangles <= budget);
      assert(lods.lod1.triangles * 5 <= lods.lod0.triangles);
      const reviewPath = 'review/' + slug + '.png';
      const digest = sha256(bytes);
      const sheet = readFileSync(join(__dirname, reviewPath));
      assert(sheet.includes(Buffer.from('tEXtGLB SHA-256\0' + digest)),
        'Review contact sheet must be rendered from this GLB');
      const review = { file: reviewPath, sha256: sha256(sheet), glb_sha256: digest };
      results.push({
        file, sha256: digest, bytes: bytes.length,
        triangles: {
          lod0: lods.lod0.triangles, lod1: lods.lod1.triangles,
          total: lods.lod0.triangles + lods.lod1.triangles, lod0_limit: budget,
        },
        size_metres: { x_width: lods.lod0.size_metres[0], y_height: lods.lod0.size_metres[1], z_depth: lods.lod0.size_metres[2] },
        materials,
        parts: { lod0: lods.lod0.parts, lod1: lods.lod1.parts },
        bounds_metres: { lod0: lods.lod0.bounds_metres, lod1: lods.lod1.bounds_metres },
        validator: { version: report.validatorVersion, errors: report.issues.numErrors, warnings: report.issues.numWarnings },
        review,
      });
      console.log(file, lods.lod0.triangles, lods.lod1.triangles, bytes.length, '0 errors, 0 warnings');
    } catch (error) {
      throw new Error(`${file}: ${error.message}`, { cause: error });
    }
  }
  writeFileSync(join(__dirname, 'models.json'), JSON.stringify(results, null, 2) + '\n');
}
main().catch(error => {
  console.error(error);
  process.exitCode = 1;
});

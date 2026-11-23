import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {readFile} from 'node:fs/promises';
import {fileURLToPath} from 'node:url';

const manifest = JSON.parse(await readFile(new URL('./manifest.json', import.meta.url), 'utf8'));
const mall = new URL('../../../../../Webpage-Design-Gallery-chibi-crowd/demos/corporate/gjh/v11/', import.meta.url);
const {loadStaticAsset} = await import(new URL('assets/static-asset.js', mall));
const three = await import(new URL('vendor/three.module.min.js', mall));
const budgets = new Map([
  ['bench_oak', [1200, 1.40, .45, .42]],
  ['counter_shop', [1500, 1.80, 1.05, .60]],
  ['wall_art', [400, .90, .90, .05]],
  ['desk_service', [1800, 1.60, 1.05, .70]],
  ['lamp_pendant', [1200, .38, .85, .38]],
  ['lamp_floor', [1500, .60, 1.70, .60]],
  ['planter_round', [1800, .75, 1.40, .75]],
  ['rack_clothes', [1200, 1.20, 1.60, .45]],
  ['ottoman_round', [800, .70, .45, .70]],
  ['shelf_display', [1500, .90, 1.80, .35]],
  ['sign_directory', [1400, .75, 1.95, .25]],
  ['table_display', [1000, 1.10, .85, .60]],
].map(([suffix, constraints]) => ['GJH_NEW_' + suffix, constraints]));

function near(actual, expected) {
  assert(actual.length === expected.length && actual.every((value, axis) =>
    Number.isFinite(value) && Math.abs(value - expected[axis]) <= .001),
  'Measured ' + actual + ' differs from ' + expected);
}

function verifyGeometry(record, entry, cap) {
  const bounds = new three.Box3();
  const vertex = new three.Vector3();
  const vertices = new Map();
  const edges = new Map();
  const top = new three.Box3();
  const aPosition = new three.Vector3(), bPosition = new three.Vector3(), cPosition = new three.Vector3();
  let tris = 0, signedVolume = 0;
  for (const {geometry, matrix, material} of record.primitives) {
    const positions = geometry.getAttribute('position');
    const mapped = [];
    for (let i = 0; i < positions.count; i++) {
      vertex.fromBufferAttribute(positions, i).applyMatrix4(matrix);
      bounds.expandByPoint(vertex);
      if (vertex.y >= -.005) top.expandByPoint(vertex);
      // Collapse material and normal seams at export-identical positions.
      const key = vertex.toArray().join(',');
      if (!vertices.has(key)) vertices.set(key, vertices.size);
      mapped.push(vertices.get(key));
    }
    const indices = geometry.index;
    assert.equal(indices.count % 3, 0);
    assert(!material.map && !material.normalMap && !material.roughnessMap && !material.metalnessMap);
    for (let i = 0; i < indices.count; i += 3) {
      const a = mapped[indices.getX(i)], b = mapped[indices.getX(i + 1)], c = mapped[indices.getX(i + 2)];
      assert(new Set([a, b, c]).size === 3, 'Coincident triangle endpoints');
      aPosition.fromBufferAttribute(positions, indices.getX(i)).applyMatrix4(matrix);
      bPosition.fromBufferAttribute(positions, indices.getX(i + 1)).applyMatrix4(matrix);
      cPosition.fromBufferAttribute(positions, indices.getX(i + 2)).applyMatrix4(matrix);
      signedVolume += aPosition.dot(bPosition.cross(cPosition)) / 6;
      for (const [v, w] of [[a, b], [b, c], [c, a]]) {
        const key = v < w ? v + ',' + w : w + ',' + v;
        const state = edges.get(key) ?? [0, 0];
        state[0]++;
        state[1] += v < w ? 1 : -1;
        edges.set(key, state);
      }
    }
    tris += indices.count / 3;
  }
  assert.equal(tris, entry.tris);
  assert(tris <= cap);
  near(bounds.min.toArray(), entry.bounds_min);
  near(bounds.max.toArray(), entry.bounds_max);
  const measuredSize = bounds.getSize(vertex).toArray();
  near(measuredSize, entry.dimensions_m);
  const maxDimensionError = Math.max(...measuredSize.map((value, i) => Math.abs(value - entry.dimensions_m[i])));
  if (entry.id.endsWith('wall_art')) {
    near(bounds.min.toArray(), [-.45, -.45, 0]);
  } else if (entry.id.endsWith('lamp_pendant')) {
    near([bounds.min.y, bounds.max.y], [-.85, 0]);
    top.getCenter(vertex);
    near([vertex.x, vertex.z], [0, 0]);
  } else {
    near([bounds.min.x, bounds.min.y, bounds.min.z],
      [-entry.dimensions_m[0] / 2, 0, -entry.dimensions_m[2] / 2]);
  }
  const topology = {boundary_edges: 0, nonmanifold_edges: 0, winding_edges: 0};
  for (const [count, orientation] of edges.values()) {
    if (count === 1) topology.boundary_edges++;
    else if (count > 2) topology.nonmanifold_edges++;
    else if (orientation) topology.winding_edges++;
  }
  if (Object.values(entry.topology.source_after_weld).every(count => count === 0)) {
    assert(Object.values(topology).every(count => count === 0), 'Closed source lost its closure');
    assert(signedVolume > 0, 'Closed mesh has reversed winding');
  }
  return {topology, max_dimension_error_m: maxDimensionError};
}

export async function verify(validateBytes, {partial = false} = {}) {
  const expected = new Map(budgets);
  const results = [];
  const existingFetch = globalThis.fetch;
  try {
    for (const entry of manifest) {
      const [cap, ...size] = expected.get(entry.id);
      expected.delete(entry.id);
      assert.equal(entry.file, entry.id + '.glb');
      assert.deepEqual(entry.dimensions_m, size);
      const url = new URL(entry.file, import.meta.url);
      const bytes = await readFile(url);
      assert(bytes.length === entry.bytes && bytes.length <= 250000);
      assert.equal(createHash('sha256').update(bytes).digest('hex'), entry.sha256);
      const source = await readFile(new URL(entry.source, import.meta.url));
      assert.equal(createHash('sha256').update(source).digest('hex'), entry.source_sha256);
      assert.equal(bytes.toString('ascii', 0, 4), 'glTF');
      assert.equal(bytes.readUInt32LE(4), 2);
      assert.equal(bytes.readUInt32LE(8), bytes.length);
      assert.equal(bytes.toString('ascii', 16, 20), 'JSON');
      const json = JSON.parse(bytes.toString('utf8', 20, 20 + bytes.readUInt32LE(12)));
      for (const field of ['images', 'textures', 'samplers', 'animations', 'skins', 'extensionsRequired']) {
        assert(!json[field]?.length, entry.file + ' contains ' + field);
      }
      assert(json.buffers.every(buffer => !buffer.uri));
      const roots = json.scenes[json.scene ?? 0].nodes;
      assert.equal(roots.length, 1);
      const root = json.nodes[roots[0]];
      assert.equal(root.name, entry.id);
      assert.deepEqual(root.extras, {asset_id: entry.id});
      assert(json.nodes.every(node => node.skin === undefined && node.weights === undefined));
      const primitives = json.meshes.flatMap(mesh => mesh.primitives);
      assert(primitives.length > 0 && primitives.length <= 16);
      for (const primitive of primitives) {
        assert((primitive.mode ?? 4) === 4 && primitive.attributes.POSITION !== undefined);
        assert(!primitive.targets && !('TEXCOORD_0' in primitive.attributes));
      }
      assert(json.materials.length > 0 && json.materials.length <= 6);
      assert.deepEqual(json.materials.map(material => material.name), entry.materials);
      for (const material of json.materials) {
        const {metallicFactor = 1, roughnessFactor = 1, baseColorFactor} = material.pbrMetallicRoughness;
        assert.equal(baseColorFactor[3], 1);
        if (material.name === 'Brushed brass') {
          assert(Math.abs(metallicFactor - .8) < 1e-6 && Math.abs(roughnessFactor - .35) < 1e-6);
        } else {
          assert(metallicFactor === 0 && roughnessFactor >= .5 && roughnessFactor <= .850001);
        }
      }
      const validation = await validateBytes(new Uint8Array(bytes), {uri: entry.file});
      assert.equal(validation.issues.numErrors, 0, JSON.stringify(validation.issues.messages));
      // Exercise the unchanged v11 loader against a disk-backed fetch. No HTTP.
      globalThis.fetch = async target => {
        assert.equal(fileURLToPath(target), fileURLToPath(url));
        return new Response(bytes);
      };
      const record = await loadStaticAsset(three, {...entry, asset_id: entry.id}, new URL('.', import.meta.url));
      assert.equal(record.status, 'loaded', entry.file + ': ' + record.reason);
      assert.equal(record.primitives.length, primitives.length);
      const geometry = verifyGeometry(record, entry, cap);
      assert.equal(Object.keys(entry.renders).length, 3);
      for (const [file, digest] of Object.entries(entry.renders)) {
        const image = await readFile(new URL(file, import.meta.url));
        assert.equal(image.toString('hex', 0, 8), '89504e470d0a1a0a');
        assert.equal(image.readUInt32BE(16), 512);
        assert.equal(image.readUInt32BE(20), 512);
        assert.equal(createHash('sha256').update(image).digest('hex'), digest);
      }
      const result = {id: entry.id, sha256: entry.sha256, errors: validation.issues.numErrors,
        warnings: validation.issues.numWarnings, primitives: primitives.length, loader: record.status, ...geometry};
      results.push(result);
      console.log(entry.id, triSummary(entry), 'Khronos', result.errors, 'errors', result.warnings,
        'warnings, v11 loader', result.loader);
    }
    if (!partial) assert.equal(expected.size, 0, 'Missing ' + [...expected.keys()].join(', '));
  } finally {
    globalThis.fetch = existingFetch;
  }
  return results;
}

function triSummary(entry) {
  return entry.tris + ' triangles, ' + entry.bytes + ' bytes,';
}

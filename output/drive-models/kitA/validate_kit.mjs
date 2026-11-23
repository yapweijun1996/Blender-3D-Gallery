import assert from 'node:assert/strict';
import { readFile, writeFile } from 'node:fs/promises';
import validator from 'gltf-validator';

const entries = [
  ['car_hatchback', 2500, [1.75, 1.45, 4.0], 'paint glass tire light trim metal'],
  ['car_sedan', 2800, [1.8, 1.45, 4.6], 'paint glass tire light trim metal'],
  ['bus', 3500, [2.5, 3.2, 11], 'paint glass tire light trim'],
  ['motorbike', 900, [null, null, 1.9]],
  ['street_lamp', 450, [null, 9, null], 'metal light'],
  ['traffic_light', 400, [null, 5, null]],
  ['sign_gantry', 700, [14, null, null]],
  ['bus_stop', 900, [3.5, null, null]],
  ['guardrail', 250, [null, null, 4]],
  ['road_cone', 120, []],
];
const allowed = 'paint glass tire light trim wall roof window leaf trunk metal concrete'.split(' ');
const epsilon = 0.00001;

function readAccessor(document, binary, number) {
  const accessor = document.accessors[number];
  const view = document.bufferViews[accessor.bufferView];
  const fields = accessor.type === 'VEC3' ? 3 : 1;
  const formats = { 5123: ['readUInt16LE', 2], 5125: ['readUInt32LE', 4], 5126: ['readFloatLE', 4] };
  const [read, bytes] = formats[accessor.componentType];
  const start = (view.byteOffset ?? 0) + (accessor.byteOffset ?? 0);
  const stride = view.byteStride ?? fields * bytes;
  return Array.from({ length: accessor.count }, (_, i) => {
    const offset = start + i * stride;
    return fields === 1 ? binary[read](offset) :
      Array.from({ length: fields }, (_, j) => binary[read](offset + j * bytes));
  });
}

function isTriangle(a, b, c) {
  const [ux, uy, uz] = b.map((value, i) => value - a[i]);
  const [vx, vy, vz] = c.map((value, i) => value - a[i]);
  return Math.hypot(uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx) > 1e-11;
}

function inspect(file, bytes, limit, expectedSize, required) {
  assert.equal(bytes.toString('ascii', 0, 4), 'glTF', file);
  const jsonSize = bytes.readUInt32LE(12);
  const doc = JSON.parse(bytes.toString('utf8', 20, 20 + jsonSize));
  const binary = bytes.subarray(28 + jsonSize);
  for (const field of ['images', 'textures', 'skins', 'animations', 'cameras', 'extensionsUsed']) {
    assert.equal(doc[field]?.length ?? 0, 0, `${file} contains ${field}`);
  }
  assert.equal(doc.buffers.length, 1, file);
  assert.equal(doc.buffers[0].uri, undefined, file);
  assert.equal(doc.meshes.length, 1, file);
  assert.equal(doc.nodes.length, 1, file);
  for (const field of ['translation', 'rotation', 'scale', 'matrix']) {
    assert.equal(doc.nodes[0][field], undefined, `${file} has a node ${field}`);
  }
  const primitives = doc.meshes[0].primitives;
  assert(primitives.length > 0 && primitives.length <= 16, file);
  const materials = doc.materials.map(mat => mat.name).sort();
  assert(materials.every(name => allowed.includes(name)), file);
  assert.equal(new Set(materials).size, materials.length, file);
  if (required) assert.deepEqual(materials, required.split(' ').sort(), file);
  if (materials.includes('paint')) {
    const paint = doc.materials.find(mat => mat.name === 'paint').pbrMetallicRoughness;
    assert(paint.baseColorFactor.slice(0, 3).every(ch => ch > .75), file);
  }

  let triangles = 0;
  const minimum = [Infinity, Infinity, Infinity];
  const maximum = [-Infinity, -Infinity, -Infinity];
  const positions = [];
  for (const primitive of primitives) {
    assert.equal(primitive.mode ?? 4, 4, file);
    const vertices = readAccessor(doc, binary, primitive.attributes.POSITION);
    const normals = readAccessor(doc, binary, primitive.attributes.NORMAL);
    const indices = readAccessor(doc, binary, primitive.indices);
    assert.equal(vertices.length, normals.length, file);
    for (const normal of normals) assert(Math.abs(Math.hypot(...normal) - 1) < .0001, file);
    for (let i = 0; i < indices.length; i += 3) {
      const tri = indices.slice(i, i + 3).map(index => vertices[index]);
      assert(isTriangle(...tri), `${file} contains a degenerate triangle at ${JSON.stringify(tri)}`);
    }
    triangles += indices.length / 3;
    for (const vertex of vertices) {
      for (let axis = 0; axis < 3; axis++) {
        minimum[axis] = Math.min(minimum[axis], vertex[axis]);
        maximum[axis] = Math.max(maximum[axis], vertex[axis]);
      }
      positions.push(vertex);
    }
  }
  assert(triangles > 0 && triangles <= limit, `${file} has ${triangles}/${limit} triangles`);
  assert(Math.abs(minimum[1]) < epsilon, `${file} does not sit on y=0`);
  const size = minimum.map((lower, i) => maximum[i] - lower);
  expectedSize.forEach((target, axis) => {
    if (target !== null) assert(Math.abs(size[axis] - target) < epsilon, `${file} size ${size}`);
  });
  if (file === 'street_lamp.glb') {
    assert(Math.abs(maximum[0] - 2.5) < epsilon, 'Lamp outreach must end at X=+2.5 m');
  }
  if (file === 'sign_gantry.glb') {
    const overhead = positions.filter(([x]) => Math.abs(x) < 6.4);
    assert(Math.abs(Math.min(...overhead.map(p => p[1])) - 6.5) < epsilon, 'Gantry clearance');
  }
  if (file === 'guardrail.glb') {
    const end = z => [...new Set(positions.filter(p => Math.abs(p[2] - z) < epsilon)
      .map(p => p.slice(0, 2).join(',')))].sort();
    assert(end(-2).length >= 20, 'Guardrail end profile is incomplete');
    assert.deepEqual(end(-2), end(2), 'Z-axis tile ends have different profiles');
  }
  return { file, triangles, bytes: bytes.length, size_m: size.map(value => Number(value.toFixed(4))), materials };
}

const manifest = [];
const failures = [];
for (const [name, maxTriangles, size, materials] of entries) {
  const file = `${name}.glb`;
  try {
    const bytes = await readFile(new URL(file, import.meta.url));
    const report = await validator.validateBytes(new Uint8Array(bytes), { uri: file, maxIssues: 0 });
    const { numErrors, numWarnings, messages } = report.issues;
    assert(numErrors === 0 && numWarnings === 0, JSON.stringify(messages));
    const model = inspect(file, bytes, maxTriangles, size, materials);
    manifest.push(model);
    console.log(`${file}: ${model.triangles} tris | ${(model.bytes / 1000).toFixed(2)} KB | ${model.size_m.join(' × ')} m | 0 errors, 0 warnings`);
  } catch (error) {
    failures.push(file);
    console.error(`${file}: ${error.message}`);
  }
}
if (failures.length) process.exitCode = 1;
else await writeFile(new URL('models.json', import.meta.url), JSON.stringify(manifest, null, 2) + '\n');

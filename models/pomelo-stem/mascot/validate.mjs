/** Measure the Pomelo GLBs, compare their metadata, and run Khronos validation. */
import fs from 'node:fs';
import path from 'node:path';
import {createRequire} from 'node:module';
import {fileURLToPath} from 'node:url';

const require = createRequire(import.meta.url);
const validator = require('gltf-validator');
const root = path.dirname(fileURLToPath(import.meta.url));
const metadata = JSON.parse(fs.readFileSync(path.join(root, 'metadata.json'), 'utf8'));
const checks = [];
const near = (actual, expected, tolerance = 1e-8) => Math.abs(actual - expected) <= tolerance;
function check(condition, message) {
  if (!condition) throw new Error(message);
}

function readGlb(bytes, filename) {
  check(bytes.length >= 20, `${filename}: truncated GLB`);
  check(bytes.toString('ascii', 0, 4) === 'glTF', `${filename}: GLB magic`);
  check(bytes.readUInt32LE(4) === 2, `${filename}: GLB version`);
  check(bytes.readUInt32LE(8) === bytes.length, `${filename}: declared byte length`);
  let document;
  let binary;
  for (let offset = 12; offset < bytes.length;) {
    check(offset + 8 <= bytes.length, `${filename}: truncated chunk header`);
    const length = bytes.readUInt32LE(offset);
    const type = bytes.readUInt32LE(offset + 4);
    const start = offset + 8;
    const end = start + length;
    check(end <= bytes.length, `${filename}: truncated chunk`);
    const chunk = bytes.subarray(start, end);
    if (type === 0x4e4f534a) document = JSON.parse(chunk.toString('utf8'));
    if (type === 0x004e4942) binary = chunk;
    offset = end;
  }
  check(document && binary, `${filename}: JSON and BIN chunks required`);
  return {document, binary};
}

function identity() {
  return [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1];
}

function localMatrix(node) {
  if (node.matrix) return node.matrix;
  const [x, y, z, w] = node.rotation ?? [0, 0, 0, 1];
  const [sx, sy, sz] = node.scale ?? [1, 1, 1];
  const [tx, ty, tz] = node.translation ?? [0, 0, 0];
  return [
    (1 - 2 * y * y - 2 * z * z) * sx,
    (2 * x * y + 2 * z * w) * sx,
    (2 * x * z - 2 * y * w) * sx,
    0,
    (2 * x * y - 2 * z * w) * sy,
    (1 - 2 * x * x - 2 * z * z) * sy,
    (2 * y * z + 2 * x * w) * sy,
    0,
    (2 * x * z + 2 * y * w) * sz,
    (2 * y * z - 2 * x * w) * sz,
    (1 - 2 * x * x - 2 * y * y) * sz,
    0,
    tx, ty, tz, 1,
  ];
}

function multiply(a, b) {
  const result = new Array(16).fill(0);
  for (let column = 0; column < 4; column++) {
    for (let row = 0; row < 4; row++) {
      for (let k = 0; k < 4; k++) result[column * 4 + row] += a[k * 4 + row] * b[column * 4 + k];
    }
  }
  return result;
}

function measure(document, binary, bytes, filename) {
  check(document.asset?.version === '2.0', `${filename}: glTF 2.0 required`);
  check(!(document.images?.length || document.textures?.length), `${filename}: unexpected image or texture`);
  check((document.buffers ?? []).every(buffer => buffer.uri === undefined), `${filename}: external buffer URI`);
  check((document.animations ?? []).length === 0, `${filename}: expected zero animation clips`);

  const scene = document.scenes?.[document.scene ?? 0];
  check(scene && scene.nodes?.length === 1, `${filename}: expected one scene root`);
  const sceneRoot = document.nodes[scene.nodes[0]];
  check(sceneRoot?.name === 'PomeloStemMascot', `${filename}: wrong scene root (${sceneRoot?.name})`);

  let triangles = 0;
  const positionAccessors = new Set();
  const min = [Infinity, Infinity, Infinity];
  const max = [-Infinity, -Infinity, -Infinity];
  const nodeNames = [];
  const visited = new Set();

  function visit(index, parentMatrix) {
    check(!visited.has(index), `${filename}: cyclic or repeated node in scene`);
    visited.add(index);
    const node = document.nodes[index];
    nodeNames.push(node.name ?? '');
    const matrix = multiply(parentMatrix, localMatrix(node));
    if (node.mesh !== undefined) {
      for (const primitive of document.meshes[node.mesh].primitives) {
        check((primitive.mode ?? 4) === 4, `${filename}: non-triangle primitive`);
        const positionIndex = primitive.attributes?.POSITION;
        const positions = document.accessors[positionIndex];
        check(positions?.componentType === 5126 && positions.type === 'VEC3', `${filename}: positions must be float VEC3`);
        positionAccessors.add(positionIndex);
        const indexAccessor = primitive.indices === undefined
          ? positions
          : document.accessors[primitive.indices];
        check(indexAccessor.count % 3 === 0, `${filename}: incomplete triangle`);
        triangles += indexAccessor.count / 3;

        const view = document.bufferViews[positions.bufferView];
        const start = (view.byteOffset ?? 0) + (positions.byteOffset ?? 0);
        const stride = view.byteStride ?? 12;
        check((view.buffer ?? 0) === 0, `${filename}: unsupported position buffer`);
        for (let vertex = 0; vertex < positions.count; vertex++) {
          const offset = start + vertex * stride;
          const p = [0, 1, 2].map(axis => binary.readFloatLE(offset + axis * 4));
          const point = [0, 1, 2].map(axis =>
            matrix[axis] * p[0] + matrix[4 + axis] * p[1] + matrix[8 + axis] * p[2] + matrix[12 + axis]);
          for (let axis = 0; axis < 3; axis++) {
            check(Number.isFinite(point[axis]), `${filename}: non-finite transformed vertex`);
            min[axis] = Math.min(min[axis], point[axis]);
            max[axis] = Math.max(max[axis], point[axis]);
          }
        }
      }
    }
    for (const child of node.children ?? []) visit(child, matrix);
  }

  for (const index of scene.nodes) visit(index, identity());
  const dimensions = max.map((value, axis) => value - min[axis]);
  return {
    bytes: bytes.length,
    triangles,
    vertices: [...positionAccessors].reduce((sum, index) => sum + document.accessors[index].count, 0),
    animations: (document.animations ?? []).length,
    root: sceneRoot.name,
    min,
    max,
    dimensions,
    nodeNames,
    images: document.images?.length ?? 0,
    textures: document.textures?.length ?? 0,
  };
}

function checkMetrics(actual, expected, label) {
  check(expected && actual.bytes === expected.glb_bytes, `${label}: metadata byte count mismatch`);
  check(actual.triangles === expected.triangles, `${label}: metadata triangle count mismatch`);
  check(actual.vertices === expected.vertices, `${label}: metadata vertex count mismatch`);
  check(actual.animations === expected.animations, `${label}: metadata animation count mismatch`);
}

function checkBounds(actual, expected, label) {
  check(expected, `${label}: missing measured bounds`);
  for (let axis = 0; axis < 3; axis++) {
    check(near(actual.min[axis], expected.min[axis]), `${label}: minimum bound mismatch on axis ${axis}`);
    check(near(actual.max[axis], expected.max[axis]), `${label}: maximum bound mismatch on axis ${axis}`);
    check(near(actual.dimensions[axis], expected.dimensions[axis]), `${label}: dimension mismatch on axis ${axis}`);
  }
}

check(metadata.id === 'pomelo-stem-mascot', 'metadata asset id');
check(metadata.root_node === 'PomeloStemMascot', 'metadata root node');
check(metadata.blender_version === '5.2.3 LTS', 'measured Blender version');
check(metadata.display?.previewRotationY === 0, 'preview rotation');
check(metadata.display?.front_axis === '+Z', 'front axis');
check(metadata.display?.previewCameraDirection?.[2] > 0, 'preview camera must face the model front (+Z)');
check(metadata.rights === "Original asset; reuse in the owner's projects is authorized. Public redistribution terms have not been specified.", 'license wording');
check(fs.statSync(path.join(root, 'pomelo-stem-mascot.blend')).size > 0, 'missing Blender source file');
for (const preview of ['front.webp', 'side.webp', 'back.webp', '3q.webp', 'expressions.webp']) {
  check(fs.statSync(path.join(root, 'previews', preview)).size > 0, `missing preview ${preview}`);
}
check(fs.statSync(path.join(root, 'previews/front.webp')).size < 150 * 1024, 'front thumbnail exceeds 150 KiB');

const report = {validator: validator.version(), assets: {}};
for (const [key, filename] of [
  ['hero', 'pomelo-stem-mascot.glb'],
  ['stand', 'pomelo-stem-mascot-stand.glb'],
  ['kit', 'pomelo-stem-mascot-kit.glb'],
]) {
  const file = path.join(root, 'exports', filename);
  const bytes = fs.readFileSync(file);
  const result = await validator.validateBytes(new Uint8Array(bytes), {uri: filename, maxIssues: 1000});
  check(result.issues.numErrors === 0, `${filename}: Khronos errors`);
  check(result.issues.numWarnings === 0, `${filename}: Khronos warnings`);
  const {document, binary} = readGlb(bytes, filename);
  const measured = measure(document, binary, bytes, filename);
  const mounts = measured.nodeNames.filter(name => /^Mount_\d\d_Expression_/.test(name));

  if (key === 'hero') {
    checkMetrics(measured, metadata.metrics, 'hero');
    checkBounds(measured, metadata.geometry?.bounds_glTF_m, 'hero geometry');
    check(near(measured.dimensions[1], metadata.geometry.height_metres), 'hero measured height mismatch');
    check(measured.triangles < 40000 && measured.bytes < 2 * 1024 ** 2, 'hero exceeds asset budgets');
  } else {
    checkMetrics(measured, metadata.additional_exports?.[key], key);
    if (key === 'stand') check(measured.triangles < 40000 && measured.bytes < 2 * 1024 ** 2, 'stand exceeds asset budgets');
    if (key === 'kit') {
      check(measured.bytes < 5 * 1024 ** 2, 'kit exceeds 5 MiB');
      check(mounts.length === 6, 'kit must contain six expression mounts');
      check(mounts.join(',') === [
        'Mount_01_Expression_Happy', 'Mount_02_Expression_Laugh', 'Mount_03_Expression_Surprised',
        'Mount_04_Expression_Wink', 'Mount_05_Expression_Thinking', 'Mount_06_Expression_Sad',
      ].join(','), 'kit expression mount order');
    }
  }
  report.assets[key] = {
    filename,
    bytes: measured.bytes,
    triangles: measured.triangles,
    vertices: measured.vertices,
    animations: measured.animations,
    root: measured.root,
    min: measured.min,
    max: measured.max,
    dimensions: measured.dimensions,
    mounts,
    validator: result.issues,
  };
}

check(metadata.validation?.errors === 0 && metadata.validation?.warnings === 0, 'metadata Khronos validation results');
check(metadata.validation.validator === validator.version(), 'metadata validator version');
console.log(JSON.stringify(report, null, 2));

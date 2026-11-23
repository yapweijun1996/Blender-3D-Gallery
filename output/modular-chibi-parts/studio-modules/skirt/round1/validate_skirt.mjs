import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import validator from "gltf-validator";

const here = path.dirname(fileURLToPath(import.meta.url));
const garmentPath = path.join(here, "skirt_v1.glb");
const sourcePath = path.join(here, "../source_studio_segmented.glb");
const bodyPath = path.join(here, "../../../master/base_body.glb");

function readGlb(filename) {
  const bytes = fs.readFileSync(filename);
  assert.equal(bytes.toString("ascii", 0, 4), "glTF");
  assert.equal(bytes.readUInt32LE(8), bytes.length);
  const jsonBytes = bytes.readUInt32LE(12);
  const document = JSON.parse(bytes.toString("utf8", 20, 20 + jsonBytes));
  const binary = bytes.subarray(28 + jsonBytes);
  return { bytes, document, binary };
}

function hash(buffer) {
  return createHash("sha256").update(buffer).digest("hex");
}

function getBuffer(glb, id) {
  const view = glb.document.bufferViews[id];
  const start = view.byteOffset ?? 0;
  return glb.binary.subarray(start, start + view.byteLength);
}

function readAccessor(glb, index) {
  const header = glb.document.accessors[index];
  const view = glb.document.bufferViews[header.bufferView];
  const components = { SCALAR: 1, VEC2: 2, VEC3: 3, VEC4: 4, MAT4: 16 }[header.type];
  const formats = {
    5121: [1, "readUInt8"], 5123: [2, "readUInt16LE"],
    5125: [4, "readUInt32LE"], 5126: [4, "readFloatLE"],
  };
  const [size, method] = formats[header.componentType];
  const buffer = getBuffer(glb, header.bufferView);
  const stride = view.byteStride ?? components * size;
  return Array.from({ length: header.count }, (_, i) =>
    Array.from({ length: components }, (_, c) =>
      buffer[method]((header.byteOffset ?? 0) + i * stride + c * size)));
}

function joints(glb) {
  const [skin] = glb.document.skins;
  const inverse = readAccessor(glb, skin.inverseBindMatrices);
  return Object.fromEntries(skin.joints.map((id, i) => [glb.document.nodes[id].name, inverse[i]]));
}

const garment = readGlb(garmentPath);
const studio = readGlb(sourcePath);
const master = readGlb(bodyPath);
const document = garment.document;
assert.equal(document.meshes.length, 1);
assert.equal(document.skins.length, 1);
assert.equal(document.animations?.length ?? 0, 0);
const masterJoints = joints(master);
const garmentJoints = joints(garment);
assert.equal(Object.keys(garmentJoints).length, 65);
assert.deepEqual(Object.keys(garmentJoints).sort(), Object.keys(masterJoints).sort());
const inverseBindDelta = Math.max(...Object.entries(garmentJoints).flatMap(([name, values]) =>
  values.map((value, i) => Math.abs(value - masterJoints[name][i]))));
assert.ok(inverseBindDelta < 1e-5);

const points = new Map();
const edges = new Map();
const deck = [];
let triangles = 0;
let vertices = 0;
let maxInfluences = 0;
let maxWeightError = 0;
let collapsedTriangles = 0;
let zeroAreaUvTriangles = 0;
for (const primitive of document.meshes[0].primitives) {
  const { POSITION, JOINTS_0, WEIGHTS_0, TEXCOORD_0, WEIGHTS_1 } = primitive.attributes;
  assert.equal(WEIGHTS_1, undefined);
  assert.notEqual(TEXCOORD_0, undefined);
  const position = readAccessor(garment, POSITION);
  const indices = readAccessor(garment, primitive.indices).flat();
  const weights = readAccessor(garment, WEIGHTS_0);
  const jointIds = readAccessor(garment, JOINTS_0);
  const texCoords = readAccessor(garment, TEXCOORD_0);
  vertices += position.length;
  const ids = position.map((xyz) => {
    const key = xyz.map((value) => Math.round(value * 1e7)).join(",");
    if (!points.has(key)) points.set(key, points.size);
    return points.get(key);
  });
  for (let i = 0; i < indices.length; i += 3) {
    const corners = indices.slice(i, i + 3);
    const welded = corners.map((j) => ids[j]);
    if (new Set(welded).size !== 3) collapsedTriangles += 1;
    const [[u0, v0], [u1, v1], [u2, v2]] = corners.map((j) => texCoords[j]);
    if (Math.abs((u1 - u0) * (v2 - v0) - (u2 - u0) * (v1 - v0)) < 1e-12) {
      zeroAreaUvTriangles += 1;
    }
    for (let k = 0; k < 3; k += 1) {
      const v = welded[k];
      const w = welded[(k + 1) % 3];
      const key = v < w ? `${v},${w}` : `${w},${v}`;
      if (!edges.has(key)) edges.set(key, []);
      edges.get(key).push(v < w ? 1 : -1);
    }
  }
  weights.forEach((row, i) => {
    assert.ok(row.every((value) => value >= 0 && Number.isFinite(value)));
    assert.ok(jointIds[i].every((value) => value >= 0 && value < 65));
    const active = jointIds[i].filter((_, j) => row[j] > 0);
    assert.ok(active.length > 0 && new Set(active).size === active.length);
    maxInfluences = Math.max(maxInfluences, active.length);
    maxWeightError = Math.max(maxWeightError, Math.abs(row.reduce((a, b) => a + b, 0) - 1));
  });
  triangles += indices.length / 3;
  deck.push({ material: document.materials[primitive.material].name, triangles: indices.length / 3 });
}
const boundaryEdges = [...edges.values()].filter((values) => values.length === 1).length;
const nonManifoldEdges = [...edges.values()].filter((values) => values.length > 2).length;
const windingErrors = [...edges.values()].filter((values) =>
  values.length === 2 && values[0] === values[1]).length;
assert.equal(boundaryEdges + nonManifoldEdges + windingErrors + collapsedTriangles, 0);
assert.ok(triangles <= 3500 && garment.bytes.length <= 1.2 * 1024 ** 2 && maxInfluences <= 4);
assert.ok(maxWeightError < 1e-5);

const sourceImages = Object.fromEntries(studio.document.images.map((image) =>
  [hash(getBuffer(studio, image.bufferView)), image.name]));
const result = await validator.validateBytes(new Uint8Array(garment.bytes), {
  uri: path.basename(garmentPath), maxIssues: 0,
});
const images = document.images.map((info, id) => {
  const bytes = getBuffer(garment, info.bufferView);
  const source = sourceImages[hash(bytes)];
  const details = result.info.resources.find((item) => item.pointer === `/images/${id}`).image;
  return { source, bytes: bytes.length, sha256: hash(bytes), width: details.width, height: details.height };
});
const report = {
  sha256: hash(garment.bytes),
  bytes: garment.bytes.length,
  triangles,
  primitiveTriangles: deck,
  exportedVertices: vertices,
  weldedVertices: points.size,
  boundaryEdges, nonManifoldEdges, windingErrors, collapsedTriangles, zeroAreaUvTriangles,
  joints: Object.keys(garmentJoints),
  inverseBindDelta, maxInfluences, maxWeightError, images,
  validations: { errors: result.issues.numErrors, warnings: result.issues.numWarnings },
};
fs.writeFileSync(path.join(here, "gltf_validator.json"), JSON.stringify(result, null, 2) + "\n");
fs.writeFileSync(path.join(here, "export_check.json"), JSON.stringify(report, null, 2) + "\n");
assert.equal(images.length, 2);
assert.ok(images.every((image) => /tripo_part_[16]_basecolor$/.test(image.source) &&
  Math.max(image.width, image.height) <= 1024));
assert.equal(result.issues.numErrors + result.issues.numWarnings, 0);
console.log(JSON.stringify({ bytes: report.bytes, triangles, vertices, maxInfluences, images,
  ...report.validations }, null, 2));

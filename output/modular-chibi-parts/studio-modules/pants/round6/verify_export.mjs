import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { createHash } from 'node:crypto';
import validator from 'gltf-validator';

const here = path.dirname(fileURLToPath(import.meta.url));
const glbPath = path.join(here, 'pants_v6.glb');
const bytes = fs.readFileSync(glbPath);
const sha256 = createHash('sha256').update(bytes).digest('hex');
const jsonLength = bytes.readUInt32LE(12);
const document = JSON.parse(bytes.subarray(20, 20 + jsonLength));
const bin = bytes.subarray(28 + jsonLength);
const validated = await validator.validateBytes(new Uint8Array(bytes), { uri: 'pants_v6.glb' });

function imageDimensions(asset) {
  const view = document.bufferViews[asset.bufferView];
  const start = view.byteOffset ?? 0;
  const buffer = bin.subarray(start, start + view.byteLength);
  if (asset.mimeType === 'image/png') return [buffer.readUInt32BE(16), buffer.readUInt32BE(20)];
  if (asset.mimeType === 'image/jpeg') {
    for (let i = 2; i + 9 < buffer.length;) {
      if (buffer[i] !== 255) break;
      const marker = buffer[i + 1];
      if ([192, 193, 194].includes(marker)) return [buffer.readUInt16BE(i + 7), buffer.readUInt16BE(i + 5)];
      i += 2 + buffer.readUInt16BE(i + 2);
    }
  }
  throw new Error(`Image dimensions unavailable for ${asset.mimeType}`);
}

const weights = [];
let triangles = 0;
let vertices = 0;
for (const mesh of document.meshes) {
  for (const primitive of mesh.primitives) {
    if ((primitive.mode ?? 4) !== 4) throw new Error('Non-triangle primitive');
    triangles += document.accessors[primitive.indices].count / 3;
    vertices += document.accessors[primitive.attributes.POSITION].count;
    const accessor = document.accessors[primitive.attributes.WEIGHTS_0];
    if (accessor.componentType !== 5126 || accessor.type !== 'VEC4' || primitive.attributes.WEIGHTS_1 !== undefined) {
      throw new Error('Expected at most four float influences');
    }
    const view = document.bufferViews[accessor.bufferView];
    let start = (view.byteOffset ?? 0) + (accessor.byteOffset ?? 0);
    const stride = view.byteStride ?? 16;
    for (let i = 0; i < accessor.count; i++, start += stride) {
      weights.push(Array.from({ length: 4 }, (_, index) => bin.readFloatLE(start + 4 * index)));
    }
  }
}

const images = document.images.map(image => ({
  name: image.name,
  type: image.mimeType,
  dimensions: imageDimensions(image),
  bytes: document.bufferViews[image.bufferView].byteLength,
}));
const report = {
  sha256,
  bytes: bytes.length,
  triangle_count: triangles,
  exported_vertices: vertices,
  mesh_count: document.meshes.length,
  skin_count: document.skins.length,
  joints: document.skins.map(skin => skin.joints.map(id => document.nodes[id].name)),
  animation_count: document.animations?.length ?? 0,
  camera_count: document.cameras?.length ?? 0,
  light_count: document.extensions?.KHR_lights_punctual?.lights.length ?? 0,
  max_influences: Math.max(...weights.map(row => row.filter(w => w > 0).length)),
  zero_weight_vertices: weights.filter(row => !row.some(w => w > 0)).length,
  max_weight_sum_error: Math.max(...weights.map(row => Math.abs(1 - row.reduce((a, b) => a + b, 0)))),
  material: document.materials,
  images,
  errors: validated.issues.numErrors,
  warnings: validated.issues.numWarnings,
};
report.pass = report.bytes <= 1.5 * 1024 ** 2 && report.triangle_count <= 6000
  && report.mesh_count === 1 && report.skin_count === 1 && report.joints[0].length === 65
  && report.animation_count === 0 && report.camera_count === 0 && report.light_count === 0
  && report.max_influences <= 4 && report.zero_weight_vertices === 0 && report.max_weight_sum_error <= 1e-5
  && report.material.length === 1 && images.length === 3
  && images.every(image => Math.max(...image.dimensions) <= 1024)
  && report.errors === 0 && report.warnings === 0;
fs.writeFileSync(path.join(here, 'gltf_validator.json'), JSON.stringify(validated, null, 2) + '\n');
fs.writeFileSync(path.join(here, 'export_check.json'), JSON.stringify(report, null, 2) + '\n');
console.log({ ...report, joints: report.joints.map(bank => bank.length) });
if (!report.pass) process.exitCode = 1;

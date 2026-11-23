import { createHash } from 'node:crypto';
import { readFile, readdir, writeFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { join } from 'node:path';
import validator from 'gltf-validator';

const directory = fileURLToPath(new URL('.', import.meta.url));
const sources = new URL('../../../models/', import.meta.url);
const materialNames = new Set([
  'paint', 'glass', 'tire', 'light', 'trim', 'wall', 'roof', 'window',
  'leaf', 'trunk', 'metal', 'concrete', 'chrome', 'plate',
]);
const rows = [...(await readFile(join(directory, 'build.py'), 'utf8'))
  .matchAll(/^    '([a-z-]+)': \('([a-z_]+)', (\d+)\),$/gm)];
const walkways = {
  hawker_stall: { x: 0, width: 1.50, floor: .12, headroom: 1.50, rear: -1.3, front: .80, ramp: .42 },
  chicken_rice_stall: { x: -.14, width: 1.50, floor: .12, headroom: 1.50, rear: -1.2, front: .20, ramp: .42 },
};
const metadata = [];
const failures = [];

for (const [, sourceId, name, budget] of rows) {
  const file = name + '.glb';
  const bytes = await readFile(join(directory, file));
  const report = await validator.validateBytes(bytes, { uri: file });
  const manifest = JSON.parse(bytes.subarray(20, 20 + bytes.readUInt32LE(12)));
  const primitives = manifest.meshes.flatMap(mesh => mesh.primitives);
  const materials = manifest.materials.map(material => material.name);
  const bounds = primitives.map(primitive => manifest.accessors[primitive.attributes.POSITION]);
  const min = [0, 1, 2].map(axis => Math.min(...bounds.map(bound => bound.min[axis])));
  const max = [0, 1, 2].map(axis => Math.max(...bounds.map(bound => bound.max[axis])));
  const size_m = max.map((edge, axis) => Number((edge - min[axis]).toFixed(4)));
  const triangles = primitives.reduce((sum, primitive) =>
    sum + manifest.accessors[primitive.indices].count / 3, 0);
  const errors = report.issues.numErrors;
  const warnings = report.issues.numWarnings;
  const issue = (condition, message) => { if (condition) failures.push(`${file} ${message}`); };
  issue(errors || warnings, JSON.stringify(report.issues.messages));
  issue(triangles > Number(budget), `has ${triangles}/${budget} triangles`);
  issue(primitives.length > 16 || bytes.length > 350_000, 'exceeds the primitive or byte budget');
  issue(min[1] < -0.00001 || min[1] > 0.00001, 'base is off the ground');
  issue(manifest.nodes.some(node => node.matrix || node.rotation || node.scale || node.translation),
    'node transforms must be baked');
  issue(primitives.some(primitive => (primitive.mode ?? 4) !== 4), 'all primitives must be triangles');
  issue(manifest.buffers.length !== 1 || manifest.buffers[0].uri, 'is not self-contained');
  issue(['animations', 'skins', 'cameras', 'textures', 'images'].some(key => manifest[key]?.length)
    || manifest.extensionsUsed?.includes('KHR_lights_punctual'), 'has prohibited resources');
  issue(materials.some(material => !materialNames.has(material)), 'has an unexpected material name');
  if (name === 'signal_pole') {
    const eyes = manifest.nodes.filter(node => node.name === 'light');
    issue(eyes.length !== 3
      || eyes.map(eye => eye.extras?.signalChannel).sort().join() !== 'amber,green,red'
      || eyes.some(eye => manifest.meshes[eye.mesh].primitives.length !== 1
        || materials[manifest.meshes[eye.mesh].primitives[0].material] !== 'light')
      || new Set(eyes.map(eye => manifest.meshes[eye.mesh].primitives[0].material)).size !== 3,
    'the three light primitives must be independently addressable');
  }
  if (name === 'zebra_crossing') {
    issue(size_m[0] !== 11 || size_m[1] > .0021, 'must be a flat, 11 m strip');
  }
  const walkway = walkways[name];
  if (walkway) {
    const geometry = readTriangles(bytes, manifest, primitives);
    issue(!hasClearWalkway(geometry, walkway), 'rear ramp or clear walking volume check failed');
  }
  const exportDirectory = fileURLToPath(new URL(sourceId + '/exports/', sources));
  const [original] = (await readdir(exportDirectory)).filter(path => path.endsWith('.glb'));
  const hash = data => createHash('sha256').update(data).digest('hex');
  const originalHash = hash(await readFile(join(exportDirectory, original)));
  metadata.push({
    file, triangles, budget: Number(budget), bytes: bytes.length, size_m,
    primitives: primitives.length, materials: [...new Set(materials)],
    validator: { version: report.validatorVersion, errors, warnings },
    source: `models/${sourceId}/exports/${original}`,
    source_sha256: originalHash,
    sha256: hash(bytes),
    render: `renders/${name}.png`,
    render_sha256: hash(await readFile(join(directory, 'renders', name + '.png'))),
    ...(walkway && { walkway_m: walkway }),
  });
}
if (metadata.length !== 16) failures.push('Expected 16 assets');
if (failures.length) {
  console.error(failures.join('\n'));
  process.exitCode = 1;
} else {
  await writeFile(join(directory, 'models.json'), JSON.stringify(metadata, null, 2) + '\n');
  console.log(`Validated ${metadata.length} assets with zero Khronos errors and warnings.`);
}

function readTriangles(bytes, gltf, primitives) {
  const bin = 28 + bytes.readUInt32LE(12);
  function accessor(id) {
    const data = gltf.accessors[id];
    const view = gltf.bufferViews[data.bufferView];
    return [data, bin + (view.byteOffset ?? 0) + (data.byteOffset ?? 0), view.byteStride];
  }
  return primitives.flatMap(primitive => {
    const [position, start, stride = 12] = accessor(primitive.attributes.POSITION);
    if (position.componentType !== 5126) throw Error('Expected FLOAT positions');
    const [indices, offset] = accessor(primitive.indices);
    const index = { 5121: [1, 'readUInt8'], 5123: [2, 'readUInt16LE'], 5125: [4, 'readUInt32LE'] }
      [indices.componentType];
    return Array.from({ length: indices.count / 3 }, (_, face) =>
      [0, 1, 2].map(corner => {
        const point = bytes[index[1]](offset + index[0] * (3 * face + corner));
        return [0, 1, 2].map(axis => bytes.readFloatLE(start + stride * point + 4 * axis));
      }));
  });
}

function hasClearWalkway(triangles, { x, width, floor, headroom, rear, front, ramp }) {
  const half = width / 2;
  const lower = [x - half + .001, floor + .002, rear - ramp + .001];
  const upper = [x + half - .001, floor + headroom, front];
  if (triangles.some(triangle => overlapsBox(triangle, lower, upper))) return false;

  // Sample the walkable surface along each side and down the centre of the aisle.
  return [-.48, 0, .48].every(fraction =>
    [-.99, -.75, -.5, -.25, 0, .25, .5, .75, .99].every(progress => {
      const z = rear + progress * (progress < 0 ? ramp : front - rear);
      const expected = floor * (1 + Math.min(0, progress));
      return triangles.some(triangle => touchesGround(triangle, x + width * fraction, z, expected));
    }));
}

function overlapsBox(triangle, lower, upper) {
  let clipped = triangle;
  for (let axis = 0; axis < 3 && clipped.length; axis++) {
    clipped = clip(clipped, axis, lower[axis], 1);
    clipped = clip(clipped, axis, upper[axis], -1);
  }
  return clipped.length > 0;
}

function clip(polygon, axis, plane, sign) {
  const result = [];
  for (const [i, a] of polygon.entries()) {
    const b = polygon[(i + 1) % polygon.length];
    const da = (a[axis] - plane) * sign;
    const db = (b[axis] - plane) * sign;
    if (da >= 0) result.push(a);
    if ((da >= 0) !== (db >= 0)) {
      result.push(a.map((u, k) => u + (b[k] - u) * da / (da - db)));
    }
  }
  return result;
}

function touchesGround([a, b, c], x, z, target) {
  const area = (b[2] - c[2]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[2] - c[2]);
  if (area > -1e-8) return false;
  const u = ((b[2] - c[2]) * (x - c[0]) + (c[0] - b[0]) * (z - c[2])) / area;
  const v = ((c[2] - a[2]) * (x - c[0]) + (a[0] - c[0]) * (z - c[2])) / area;
  const w = 1 - u - v;
  return Math.min(u, v, w) >= -1e-5 && Math.abs(u * a[1] + v * b[1] + w * c[1] - target) < .002;
}

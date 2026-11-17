import assert from 'node:assert/strict';
import fs from 'node:fs';
import { fileURLToPath } from 'node:url';
import { createHash } from 'node:crypto';
import { Box3, Vector3 } from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import validator from 'gltf-validator';

const dir = fileURLToPath(new URL('.', import.meta.url));
const spec = JSON.parse(fs.readFileSync(dir + 'backlog.json'));
const bytes = fs.readFileSync(process.argv[2] ?? dir + 'exports/optimized.glb');
const json = JSON.parse(bytes.subarray(20, 20 + bytes.readUInt32LE(12)));
const validation = await validator.validateBytes(new Uint8Array(bytes), { uri: 'optimized.glb', maxIssues: 200 });
if (!process.argv[2]) fs.writeFileSync(dir + 'reports/khronos.json', JSON.stringify(validation, null, 2) + '\n');
assert.equal(validation.issues.numErrors, 0);
assert.equal(validation.issues.numWarnings, 0);
assert.ok(json.buffers.every(b => !b.uri));
assert.ok(!json.images?.length && !json.textures?.length && !json.cameras?.length && !json.extensions?.KHR_lights_punctual);
assert.equal(json.materials.length, 3);
assert.ok(json.materials.every(m => !m.alphaMode || m.alphaMode === 'OPAQUE'));
const gltf = await new GLTFLoader().parseAsync(bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength), '');
gltf.scene.updateMatrixWorld(true);
assert.equal(gltf.animations.length, 0);
const root = gltf.scene.getObjectByName(spec.root);
assert.ok(root);
assert.deepEqual(root.position.toArray(), [0, 0, 0]);
assert.equal(root.userData.units, 'metres');
assert.equal(root.userData.front_axis, 'Blender -Y / glTF +Z');
const bounds = new Box3().setFromObject(root, true);
const dimensions = bounds.getSize(new Vector3()).toArray();
for (const [i, expected] of [spec.dimensions[0], spec.dimensions[2], spec.dimensions[1]].entries())
  assert.ok(Math.abs(dimensions[i] - expected) < 1e-5, 'metric envelope');
assert.ok(Math.abs(bounds.min.y) < 1e-6, 'floor datum');
assert.ok(Math.abs(bounds.getCenter(new Vector3()).x) < 1e-6, 'floor centre X');
assert.ok(Math.abs(bounds.getCenter(new Vector3()).z) < 1e-6, 'floor centre Z');
let triangles = 0, vertices = 0, primitives = 0, degenerateTriangles = 0;
const parts = {};
const a = new Vector3(), b = new Vector3(), c = new Vector3();
root.traverse(o => {
  if (!o.isMesh) return;
  const p = o.geometry.attributes.position, n = o.geometry.attributes.normal, index = o.geometry.index;
  assert.ok(n);
  assert.ok([...p.array, ...n.array].every(Number.isFinite));
  for (let i = 0; i < n.count; i++) assert.ok(Math.abs(new Vector3().fromBufferAttribute(n, i).length() - 1) < 1e-4, 'unit normals');
  const count = index?.count ?? p.count;
  vertices += p.count;
  triangles += count / 3;
  primitives++;
  for (let i = 0; i < count; i += 3) {
    a.fromBufferAttribute(p, index ? index.getX(i) : i);
    b.fromBufferAttribute(p, index ? index.getX(i + 1) : i + 1);
    c.fromBufferAttribute(p, index ? index.getX(i + 2) : i + 2);
    if (b.sub(a).cross(c.sub(a)).lengthSq() < 1e-20) degenerateTriangles++;
  }
  const box = new Box3().setFromObject(o, true);
  parts[o.name] = { min: box.min.toArray(), max: box.max.toArray(), material: o.material.name, source_parts: o.userData.source_parts };
});
assert.equal(degenerateTriangles, 0);
assert.ok(triangles <= spec.budget.triangles);
assert.ok(bytes.length < spec.budget.bytes);
assert.equal(primitives, 5);
const panelMetrics = {};
for (const [side, sign] of [['Front', 1], ['Rear', -1]]) {
  const panel = root.getObjectByName('DELIVERY_Panel' + side);
  assert.ok(panel);
  assert.ok(panel.material.emissiveIntensity > 0 && panel.material.emissive.toArray().some(v => v > 0), 'actual emissive material');
  const box = new Box3().setFromObject(panel, true);
  const size = box.getSize(new Vector3());
  assert.ok(Math.abs(size.x - .752) < 1e-5 && Math.abs(size.y - 1.408) < 1e-5 && Math.abs(size.z - .008) < 1e-5);
  assert.ok(Math.abs(box.getCenter(new Vector3()).z - sign * .068) < 1e-5, 'opposed panel placement');
  // Verify a large real outward face, rather than trusting names or extras.
  let area = 0;
  const p = panel.geometry.attributes.position, index = panel.geometry.index;
  for (let i = 0; i < index.count; i += 3) {
    a.fromBufferAttribute(p, index.getX(i)).applyMatrix4(panel.matrixWorld);
    b.fromBufferAttribute(p, index.getX(i + 1)).applyMatrix4(panel.matrixWorld);
    c.fromBufferAttribute(p, index.getX(i + 2)).applyMatrix4(panel.matrixWorld);
    const normal = b.clone().sub(a).cross(c.clone().sub(a));
    if (sign * normal.z > 0 && Math.abs(a.z - sign * .072) < 1e-5 && Math.abs(b.z - a.z) < 1e-5 && Math.abs(c.z - a.z) < 1e-5)
      area += normal.length() / 2;
  }
  assert.ok(area > 1, 'blank outward diffuser face exceeds one square metre');
  panelMetrics[side] = { dimensions: size.toArray(), outward_flat_area_m2: area };
  const structure = root.getObjectByName('DELIVERY_Structure');
  const markerBounds = new Box3();
  const positions = structure.geometry.attributes.position;
  for (let i = 0; i < positions.count; i++) {
    a.fromBufferAttribute(positions, i).applyMatrix4(structure.matrixWorld);
    if (Math.abs(a.x + sign * .175) < .021 && Math.abs(a.y - .91) < .021 && sign * a.z > .073)
      markerBounds.expandByPoint(a);
  }
  assert.ok(Math.abs(markerBounds.getSize(new Vector3()).x - .038) < 1e-5, 'real blank marker dot');
}
const light = root.getObjectByName('DELIVERY_Lightbar');
assert.ok(light && light.material.emissive.toArray().some(v => v > 0));
assert.ok(new Box3().setFromObject(light).min.y > 1.86, 'top light bar');
const report = {
  result: 'PASS', id: spec.slug, glb_bytes: bytes.length, triangles, vertices,
  primitives, materials: json.materials.length, animations: gltf.animations.length,
  degenerate_triangles: degenerateTriangles, dimensions, dimension_order: 'X width, Y height, Z depth',
  bounds: { min: bounds.min.toArray(), max: bounds.max.toArray() },
  sha256: createHash('sha256').update(bytes).digest('hex'),
  validation: { errors: validation.issues.numErrors, warnings: validation.issues.numWarnings, validator: validation.validatorVersion },
  panels: panelMetrics, parts,
  limitations: 'Static geometry and emissive appearance only. No actual map, navigation, physical lighting or full-mall performance certification.'
};
if (!process.argv[2]) fs.writeFileSync(dir + 'reports/assets.json', JSON.stringify(report, null, 2) + '\n');
console.log(JSON.stringify(report, null, 2));

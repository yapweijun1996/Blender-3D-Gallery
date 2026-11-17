// Asset-specific adaptation of the self-checkout-machine quality gate.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import { fileURLToPath } from 'node:url';
import { createHash } from 'node:crypto';
import { Box3, Vector3 } from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import validator from 'gltf-validator';

const dir = fileURLToPath(new URL('.', import.meta.url));
const bytes = fs.readFileSync(dir + 'exports/optimized.glb');
const json = JSON.parse(bytes.subarray(20, 20 + bytes.readUInt32LE(12)));
const validation = await validator.validateBytes(new Uint8Array(bytes), { maxIssues: 100 });
fs.writeFileSync(dir + 'reports/khronos.json', JSON.stringify(validation, null, 2) + '\n');
assert.equal(validation.issues.numErrors, 0);
assert.equal(validation.issues.numWarnings, 0);
assert.ok(json.buffers.every(buffer => !buffer.uri));
assert.ok(!json.images?.length && !json.textures?.length && !json.cameras?.length);
assert.ok(!json.extensions?.KHR_lights_punctual);
assert.equal(json.materials.length, 3);
assert.ok(json.materials.every(m => !m.alphaMode || m.alphaMode === 'OPAQUE'));
const gltf = await new GLTFLoader().parseAsync(bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength), '');
gltf.scene.updateMatrixWorld(true);
const root = gltf.scene.getObjectByName('ASSET_LoungeSofaBench');
assert.ok(root);
assert.deepEqual(root.position.toArray(), [0, 0, 0]);
assert.equal(root.userData.units, 'metres');
assert.equal(root.userData.front_axis, 'Blender -Y / glTF +Z');
assert.equal(gltf.animations.length, 0);
let triangles = 0, vertices = 0, primitives = 0;
const parts = {};
gltf.scene.traverse(object => {
  if (!object.isMesh) return;
  const geometry = object.geometry, position = geometry.attributes.position, index = geometry.index;
  assert.ok(geometry.attributes.normal);
  assert.ok([...position.array, ...geometry.attributes.normal.array].every(Number.isFinite));
  const count = index?.count ?? position.count;
  assert.equal(count % 3, 0);
  const a = new Vector3(), b = new Vector3(), c = new Vector3();
  for (let i = 0; i < count; i += 3) {
    a.fromBufferAttribute(position, index ? index.getX(i) : i);
    b.fromBufferAttribute(position, index ? index.getX(i + 1) : i + 1);
    c.fromBufferAttribute(position, index ? index.getX(i + 2) : i + 2);
    assert.ok(b.sub(a).cross(c.sub(a)).lengthSq() > 1e-20, 'nondegenerate triangle');
  }
  triangles += count / 3;
  vertices += position.count;
  primitives += Math.max(1, geometry.groups.length);
  const bounds = new Box3().setFromObject(object, true);
  parts[object.name] = { min: bounds.min.toArray(), max: bounds.max.toArray(), triangles: count / 3 };
});
const near = (a, b) => assert.ok(Math.abs(a - b) < 1e-5, `${a} != ${b}`);
const bounds = new Box3().setFromObject(root, true);
const dimensions = bounds.getSize(new Vector3()).toArray();
[3, .8, 2.2].forEach((expected, i) => near(dimensions[i], expected));
near(bounds.min.y, 0);
near(bounds.min.x + bounds.max.x, 0);
near(bounds.min.z + bounds.max.z, 0);
for (const name of ['BATCH_GreigeFabric', 'BATCH_GraphiteMetal', 'BATCH_WarmTableSurface']) assert.ok(parts[name]);
assert.equal(json.meshes.length, 3);
assert.ok(triangles < 15000 && bytes.length < 1572864 && primitives === 3);

const source = JSON.parse(fs.readFileSync(dir + 'reports/sources.json'));
assert.equal(source.source_materials.length, 3);
assert.equal(source.source_text_objects, 0);
const sofa = source.subassemblies.SOFA_ThreeSeat;
const bench = source.subassemblies.BENCH_Backless;
const table = source.subassemblies.TABLE_SlimShared;
[2, .85, .8].forEach((expected, i) => near(sofa.size[i], expected));
[.38, 1.6, .45].forEach((expected, i) => near(bench.size[i], expected));
[.22, .85, .5].forEach((expected, i) => near(table.size[i], expected));
for (const part of [sofa, bench, table]) near(part.min[2], 0);
assert.equal(sofa.parts.filter(n => /^SOFA_SeatCushion_/.test(n)).length, 3);
assert.equal(sofa.parts.filter(n => /^SOFA_BackCushion_/.test(n)).length, 3);
assert.equal(bench.parts.filter(n => /^BENCH_SeatCushion_/.test(n)).length, 2);
assert.ok(!bench.parts.some(n => /Back|Arm/.test(n)));
// Check usable projected space, rather than merely ordering furniture boxes.
// Source bounds are evaluated world-space bounds in Blender X,Y,Z.
const overlapsFloor = (a, b) => [0, 1].every(i => Math.min(a.max[i], b.max[i]) - Math.max(a.min[i], b.min[i]) > 1e-5);
const boxes = source.part_bounds;
const sofaLanes = [1, 2, 3].map(i => {
  const seat = boxes[`SOFA_SeatCushion_${i}`];
  const lane = { min: [seat.min[0], sofa.min[1] - .6], max: [seat.max[0], sofa.min[1]] };
  const exit = { min: [seat.min[0], bench.min[1] - .6], max: [seat.max[0], sofa.min[1]] };
  for (const obstacle of [bench, table]) {
    assert.ok(!overlapsFloor(lane, obstacle), `sofa seat ${i}: 0.6 m clear legroom`);
    assert.ok(!overlapsFloor(exit, obstacle), `sofa seat ${i}: open forward exit`);
  }
  return lane;
});
const benchLanes = [1, 2].map(i => {
  const seat = boxes[`BENCH_SeatCushion_${i}`];
  const lane = { min: [bench.min[0] - .5, seat.min[1]], max: [bench.min[0], seat.max[1]] };
  for (const obstacle of [sofa, table]) assert.ok(!overlapsFloor(lane, obstacle), `bench seat ${i}: 0.5 m clear inner use side`);
  return lane;
});
assert.ok(table.max[0] < bench.min[0] && table.max[1] < sofa.min[1], 'table inside the L');
assert.ok(bench.min[0] > sofa.max[0], 'bench never blocks a sofa seat');
const benchTableGap = bench.min[0] - table.max[0];
assert.ok(benchTableGap >= .5 - 1e-5 && benchTableGap <= .55, 'bench knee space and table reach');
const rightSeat = boxes.SOFA_SeatCushion_3;
const sofaReachPoint = [(rightSeat.min[0] + rightSeat.max[0]) / 2, rightSeat.min[1]];
const sofaTableReach = Math.hypot(...sofaReachPoint.map((v, i) => Math.max(table.min[i] - v, 0, v - table.max[i])));
assert.ok(sofaTableReach < .55, 'table end reachable from right sofa seat front');
for (const i of [1, 2]) {
  const seat = boxes[`BENCH_SeatCushion_${i}`];
  const y = (seat.min[1] + seat.max[1]) / 2;
  assert.ok(y >= table.min[1] && y <= table.max[1], 'long table edge serves both bench pads');
}
const base = boxes.SOFA_UpholsteredBase, frame = boxes.SOFA_RecessedUnderframe;
for (const name of ['SOFA_RoundedArm', 'SOFA_RoundedArm.001']) {
  const arm = boxes[name];
  near(arm.min[2], base.min[2]);
  assert.ok(arm.min[0] < base.min[0] || arm.max[0] > base.max[0], 'continuous outer arm side');
}
assert.ok(frame.min[0] > base.min[0] && frame.max[0] < base.max[0], 'underframe recessed inside fabric');
const layout = {
  arrangement: 'Open L: sofa faces +Z; perpendicular backless bench uses inward -X side',
  furniture_footprint_m: [dimensions[0], dimensions[2]], original_target_m: [3, 1.5],
  tradeoff: 'Depth increased by 0.7 m to preserve full-size seating and open sofa exits',
  sofa_clear_legroom_m: .6, bench_inner_clear_legroom_m: .5,
  bench_table_gap_m: benchTableGap, sofa_right_seat_front_to_table_m: sofaTableReach,
  sofa_lanes_blender_xy: sofaLanes, bench_lanes_blender_xy: benchLanes,
  scope: 'Evaluated AABB projection and reach allowances; not a human sitting simulation or accessibility certification'
};
const report = { result: 'PASS', id: 'lounge-sofa-bench',
  glb_bytes: bytes.length, triangles, vertices, meshes: json.meshes.length, primitives,
  materials: json.materials.length, images: json.images?.length ?? 0, animations: gltf.animations.length,
  dimensions, bounds: { min: bounds.min.toArray(), max: bounds.max.toArray() },
  sha256: createHash('sha256').update(bytes).digest('hex'),
  validation: { errors: validation.issues.numErrors, warnings: validation.issues.numWarnings },
  layout, parts };
fs.writeFileSync(dir + 'reports/assets.json', JSON.stringify(report, null, 2) + '\n');
const metadataPath = dir + 'metadata/lounge-sofa-bench.json';
if (fs.existsSync(metadataPath)) {
  const metadata = JSON.parse(fs.readFileSync(metadataPath));
  metadata.blender_version = source.blender_version;
  metadata.dimensions = { units: 'metres', axis_order: 'glTF X,Y,Z (width,height,depth)', size: dimensions, bounds: report.bounds };
  metadata.statistics = Object.fromEntries(['glb_bytes', 'triangles', 'vertices', 'meshes', 'primitives', 'materials', 'images', 'animations', 'sha256'].map(key => [key, report[key]]));
  metadata.measured_subassemblies = source.subassemblies;
  metadata.source_mesh_parts = source.source_mesh_parts;
  metadata.layout = layout;
  fs.writeFileSync(metadataPath, JSON.stringify(metadata, null, 2) + '\n');
}
console.log(JSON.stringify(report, null, 2));

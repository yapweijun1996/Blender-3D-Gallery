import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { createHash } from 'node:crypto';
import { Box3, Vector3 } from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import validator from 'gltf-validator';

const dir = path.dirname(fileURLToPath(import.meta.url));
const input = process.argv[2] || path.join(dir, 'exports/optimized.glb');
const bytes = fs.readFileSync(input);
assert.equal(bytes.toString('ascii', 0, 4), 'glTF');
assert.equal(bytes.readUInt32LE(4), 2);
assert.equal(bytes.readUInt32LE(8), bytes.length);
const json = JSON.parse(bytes.subarray(20, 20 + bytes.readUInt32LE(12)));
const validation = await validator.validateBytes(new Uint8Array(bytes));
fs.writeFileSync(path.join(dir, process.argv[2] ? 'reports/khronos-edited.json' : 'reports/khronos.json'), JSON.stringify(validation,null,2)+'\n');
assert.equal(validation.issues.numErrors, 0, JSON.stringify(validation.issues));
assert.equal(validation.issues.numWarnings, 0, JSON.stringify(validation.issues));
assert.ok(json.buffers.every(b => !b.uri));
for (const key of ['images', 'textures', 'cameras', 'skins', 'animations']) assert.equal(json[key]?.length || 0, 0, key);
assert.ok(!json.extensions?.KHR_lights_punctual);
assert.equal(json.materials.length, 2);
assert.equal(json.materials.filter(m => m.alphaMode === 'BLEND').length, 1);
for (const mesh of json.meshes) for (const primitive of mesh.primitives) {
  if (primitive.material !== undefined && json.materials[primitive.material].alphaMode !== 'BLEND') {
    assert.ok(primitive.attributes.COLOR_0 !== undefined, 'Shared opaque palette exports vertex colors');
  }
}
const gltf = await new GLTFLoader().parseAsync(bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength), '');
gltf.scene.updateMatrixWorld(true);
const root = gltf.scene.getObjectByName('ASSET_IceCreamChestFreezer');
assert.ok(root);
assert.deepEqual(root.position.toArray(), [0, 0, 0]);
assert.equal(root.userData.units, 'metres');
assert.equal(root.children.length, 4);
let triangles = 0, primitives = 0, degenerate = 0;
const a = new Vector3(), b = new Vector3(), c = new Vector3();
root.traverse(o => {
  if (!o.isMesh) return;
  primitives++;
  const g = o.geometry, positions = g.attributes.position, normals = g.attributes.normal;
  assert.ok(normals && [...normals.array].every(Number.isFinite));
  assert.ok([...positions.array].every(Number.isFinite));
  const count = g.index?.count || positions.count;
  triangles += count / 3;
  for (let i = 0; i < count; i += 3) {
    a.fromBufferAttribute(positions, g.index ? g.index.getX(i) : i);
    b.fromBufferAttribute(positions, g.index ? g.index.getX(i + 1) : i + 1);
    c.fromBufferAttribute(positions, g.index ? g.index.getX(i + 2) : i + 2);
    if (b.sub(a).cross(c.sub(a)).lengthSq() <= 1e-24) degenerate++;
  }
});
assert.equal(degenerate, 0, 'No zero-area or sub-picometre-area exported triangles');
const bounds = new Box3().setFromObject(root, true);
const dimensions = bounds.getSize(new Vector3()).toArray();
for (const [i, expected] of [1.50, .90, .75].entries()) assert.ok(Math.abs(dimensions[i] - expected) < .025, `Envelope ${dimensions}`);
assert.ok(Math.abs(bounds.min.y) < 1e-6, 'Ground datum');
assert.ok(bounds.max.z > -bounds.min.z + .005, 'Asymmetric front vent exports toward glTF +Z');
const visibleTriangles = triangles;
const collisionScene = gltf.scenes[root.userData.collision_scene];
const collider = collisionScene?.getObjectByName('collider_box');
assert.ok(collider?.isMesh && !root.getObjectByName('collider_box'), 'Collider is outside the default visual scene');
assert.equal(collider.userData.hidden, true);
const collisionNode = json.nodes.find(n => n.name === 'collider_box');
const collisionPrimitives = json.meshes[collisionNode.mesh].primitives;
assert.ok(collisionPrimitives.every(p => p.material === undefined), 'No collider material');
const collisionTriangles = collisionPrimitives.reduce((n,p) => n + json.accessors[p.indices].count / 3, 0);
assert.equal(collisionTriangles, 12);
triangles += collisionTriangles;
const colliderBounds = new Box3().setFromObject(collider, true);
assert.ok(colliderBounds.clone().expandByScalar(.00001).containsBox(bounds), 'Collider encloses the whole prop');
const budget = {triangles:8000, bytes:1048576, mesh_primitives:6, materials:2};
assert.ok(triangles <= budget.triangles && bytes.length <= budget.bytes && primitives <= budget.mesh_primitives && json.materials.length <= budget.materials);
const contents = root.getObjectByName('Contents_Geometry');
assert.equal(contents.userData.source_parts.filter(n => n.startsWith('Tub_')).length, 6);
assert.equal(contents.userData.source_parts.filter(n => n.startsWith('Frozen_')).length, 6);
const lids = ['Left', 'Right'].map(side => root.getObjectByName(`Lid_${side}_Geometry`));
assert.ok(lids.every(Boolean));
const lidBoxes = lids.map(lid => new Box3().setFromObject(lid, true));
const verticalGap = lidBoxes[1].min.y - lidBoxes[0].max.y;
assert.ok(verticalGap >= .0029, `Independent tracks and handle clearance: ${verticalGap}`);
const contentClearance = lidBoxes[0].min.y - new Box3().setFromObject(contents, true).max.y;
assert.ok(contentClearance > .07, 'Raised cream surfaces clear the entire lid sweep');
const slides = [];
for (const lid of lids) {
  const saved = lid.position.clone(), quaternion = lid.quaternion.clone();
  for (let step = 0; step <= 10; step++) {
    const t = step / 10;
    lid.position.x = lid.userData.closed_x_m * (1 - t) + lid.userData.open_x_m * t;
    root.updateMatrixWorld(true);
    const box = new Box3().setFromObject(lid, true);
    assert.ok(box.min.x >= -.701 && box.max.x <= .701, 'Slides within cabinet aperture');
    assert.equal(lid.quaternion.angleTo(quaternion), 0, 'Sliding preserves lid rotation');
    assert.ok(Math.abs(lid.position.y - saved.y) < 1e-8 && Math.abs(lid.position.z - saved.z) < 1e-8);
  }
  lid.position.copy(saved);
  slides.push({node:lid.name, closed_x_m:lid.userData.closed_x_m, open_x_m:lid.userData.open_x_m, sampled_positions:11});
}
root.updateMatrixWorld(true);
const report = {result:'PASS', glb_bytes:bytes.length, triangles, mesh_primitives:primitives,
  visible_triangles:visibleTriangles, collision_triangles:collisionTriangles,
  placement_meshes:root.children.length, stored_meshes:json.meshes.length, materials:json.materials.length, dimensions_gltf_xyz_m:dimensions,
  bounds:{min:bounds.min.toArray(), max:bounds.max.toArray()}, degenerate_triangles:degenerate,
  budget, validation:{errors:0,warnings:0,infos:validation.issues.numInfos},
  budget_source:'MallQueue/tasks/glass-door-beverage-cooler.md P1 override and explicit ice-cream-chest-freezer fallback; 1 MiB retained as a stricter local size cap',
  slides, minimum_track_clearance_m:verticalGap, minimum_contents_clearance_m:contentClearance,
  collision:{name:'collider_box',scene:root.userData.collision_scene,material:false,visible_by_default:false},
  textures:0, animation_clips:0,
  sha256:createHash('sha256').update(bytes).digest('hex'), tool_versions:{three:'0.187.0',validator:'2.0.0-dev.3.10'}};
fs.writeFileSync(path.join(dir, process.argv[2] ? 'reports/edited-assets.json' : 'reports/assets.json'), JSON.stringify(report,null,2)+'\n');
console.log(JSON.stringify(report));

import assert from 'node:assert/strict';
import RAPIER from '@dimforge/rapier3d-compat';
import { BODY, createCollisionWorld } from '../../docs/verification/mall-corridor/collision.js';
import { createPhysicsWorld, FIXED_DT } from '../../src/world/physics/world.js';
import { Vector3 } from 'three';

// The independent sweep uses the actual transformed triangles, including
// details and recesses. The visitor controller itself uses component bounds.
function triangles(object) {
  const vertices = [], indices = [];
  const point = new Vector3();
  object.traverse(mesh => {
    if (!mesh.isMesh) return;
    const first = vertices.length / 3;
    const geometry = mesh.geometry;
    const positions = geometry.getAttribute('position');
    for (let i = 0; i < positions.count; i++) {
      point.fromBufferAttribute(positions, i).applyMatrix4(mesh.matrixWorld);
      vertices.push(point.x, point.y, point.z);
    }
    const index = geometry.getIndex();
    for (let i = 0; i < (index?.count ?? positions.count); i++) {
      indices.push(first + (index ? index.getX(i) : i));
    }
  });
  assert.ok(indices.length > 0 && indices.length % 3 === 0, 'expected mesh triangles');
  return { vertices, indices };
}


// Each direct child is a placed GLB root. The same group drives both the mall
// visitor's component bounds and a separate collision world of triangle meshes.
export async function measureCorridor(root) {
  const visitor = createCollisionWorld(root);
  const physics = await createPhysicsWorld();
  const floorHandles = new Set(), obstacleIds = new Map(), modules = [];
  root.updateMatrixWorld(true);
  for (const object of root.children) {
    const id = object.userData.moduleId;
    const collider = physics.addStaticTrimesh(triangles(object));
    modules.push({ id, x: object.position.x, collider });
    if (id === 'floor' || id === 'cornerTile') floorHandles.add(collider.handle);
    else if (id !== 'floorEdge' && id !== 'mitredTrim') obstacleIds.set(collider.handle, id);
  }
  assert.equal(visitor.floors.length, floorHandles.size, 'all installed floor cells reach the visitor');
  physics.step(FIXED_DT);
  const cylinder = new RAPIER.Cylinder(BODY.height / 2, BODY.radius);
  const rotation = { x: 0, y: 0, z: 0, w: 1 };
  const surface = (x, z) => {
    const hit = physics.world.castRay(new RAPIER.Ray({ x, y: .1, z }, { x: 0, y: -1, z: 0 }), .5, true,
      undefined, undefined, undefined, undefined, collider => floorHandles.has(collider.handle));
    return hit ? .1 - hit.timeOfImpact : null;
  };
  const sweep = (start, dx, dz) => {
    const hit = physics.world.castShape({ x: start.x, y: BODY.height / 2, z: start.z }, rotation, { x: dx, y: 0, z: dz },
      cylinder, 0, 1, true, undefined, undefined, undefined, undefined, collider => obstacleIds.has(collider.handle));
    return hit && { fraction: hit.time_of_impact, module: obstacleIds.get(hit.collider.handle) };
  };
  function overlaps(id, side) {
    const subject = modules.find(module => module.id === id && Math.sign(module.x) === side);
    const origin = { x: 0, y: 0, z: 0 };
    return modules.filter(other => other !== subject && obstacleIds.has(other.collider.handle) &&
      subject.collider.shape.intersectsShape(origin, rotation, other.collider.shape, origin, rotation)).map(other => other.id);
  }
  return { surface, sweep, overlaps, visitor, dispose: () => physics.dispose() };
}

const footprint = [[0, 0], ...Array.from({ length: 24 }, (_, i) => [
  BODY.radius * Math.cos(i * Math.PI / 12), BODY.radius * Math.sin(i * Math.PI / 12),
])];
export function checkFloor(scene, p) {
  for (const [dx, dz] of footprint) {
    const y = scene.surface(p.x + dx, p.z + dz);
    // The tile's grout and bevels sink as much as 1 mm from the finished floor.
    assert.ok(y !== null && y >= -.001001 && y <= .000001,
      'unsupported footprint at ' + JSON.stringify({ x: p.x + dx, z: p.z + dz, y }));
  }
}

export function walk(scene, points) {
  const p = { ...points[0] };
  assert.equal(scene.visitor.obstruction(p), null, 'valid starting point');
  checkFloor(scene, p);
  let samples = 1, metres = 0;
  for (const target of points.slice(1)) {
    const dx = target.x - p.x, dz = target.z - p.z;
    const distance = Math.hypot(dx, dz);
    assert.equal(scene.sweep(p, dx, dz), null, 'an installed mesh obstructs the walking line');
    const count = Math.ceil(distance / BODY.step);
    for (let i = 0; i < count; i++) {
      assert.equal(scene.visitor.move(p, dx / count, dz / count), null, 'visitor route blocked');
      checkFloor(scene, p);
    }
    assert.ok(Math.hypot(target.x - p.x, target.z - p.z) < 1e-6, 'visitor reaches waypoint');
    samples += count;
    metres += distance;
  }
  return { metres: +metres.toFixed(3), samples, floorRays: samples * footprint.length };
}

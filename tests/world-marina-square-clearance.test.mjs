import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';

import RAPIER from '@dimforge/rapier3d-compat';
import { DoubleSide, Mesh, MeshBasicMaterial, Raycaster, Vector3 } from 'three';
import { cross, offsetPolyline } from '../src/world/network/geometry.js';
import { createPhysicsWorld, FIXED_DT } from '../src/world/physics/world.js';
import { buildTile, buildingMesh, TILE_SIZE } from '../src/world/tile-mesh.js';

const buildingId = 303311927;
const readTile = key => JSON.parse(readFileSync(new URL('../models/world/tiles/' + key + '.json', import.meta.url)));
const tiles = ['-2_-4', '-1_-4', '-2_-5', '-1_-5', '-3_-4', '-1_-3'].map(readTile);
const tile = tiles[0];
const building = tile.buildings.find(({ id }) => id === buildingId);
const { passages: [passage], ...uncutBuilding } = building;
const ids = ['723073393:0', '545362402:0', '545362402:1', '545362402:2', '545362403:0', '635373148:0'];
const toWorld = ([x, z]) => [x + tile.x * TILE_SIZE, z + tile.z * TILE_SIZE];
const route = ids.flatMap((id, i) => tile.roads.find(road => road.id === id).geometry.slice(i > 0 ? 1 : 0)).map(toWorld);
const outline = building.geometry.map(toWorld), opening = passage.geometry.map(toWorld);
const up = { x: 0, y: 1, z: 0 }, down = { x: 0, y: -1, z: 0 };
const point = ([x, z], y) => ({ x, y, z });

function vector(a, b) {
  const dx = b[0] - a[0], dz = b[1] - a[1], length = Math.hypot(dx, dz);
  return { direction: { x: dx / length, y: 0, z: dz / length }, length };
}

function middle(a, b, t) {
  return [a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1])];
}

function inside([x, z], ring) {
  let included = false;
  for (let i = 1; i < ring.length; i++) {
    const [ax, az] = ring[i - 1], [bx, bz] = ring[i];
    if ((az > z) !== (bz > z) && x < ax + (bx - ax) * (z - az) / (bz - az)) included = !included;
  }
  return included;
}

function cast(physics, origin, direction, length) {
  return physics.world.castRay(new RAPIER.Ray(origin, direction), length, true, RAPIER.QueryFilterFlags.ONLY_FIXED);
}

function paint(meshes, origin, direction, length) {
  return new Raycaster(new Vector3(origin.x, origin.y, origin.z), new Vector3(direction.x, direction.y, direction.z),
    0, length).intersectObjects(meshes)[0];
}

async function buildWorld(t) {
  const physics = await createPhysicsWorld();
  const material = new MeshBasicMaterial({ side: DoubleSide });
  const meshes = { ground: [], buildings: [] };
  const passages = [];
  t.after(() => {
    for (const mesh of [...meshes.ground, ...meshes.buildings]) mesh.geometry.dispose();
    material.dispose();
    physics.dispose();
  });
  const floor = physics.addGround({ halfWidth: 60000, halfDepth: 60000 });
  for (const source of tiles) {
    const built = buildTile(source);
    for (const [layer, geometries] of Object.entries({ ground: [built.ground], buildings: [built.buildings, built.towers] })) {
      for (const geometry of geometries.filter(Boolean)) meshes[layer].push(new Mesh(geometry, material));
    }
    for (const solid of built.solids) {
      const collider = physics.addStaticTrimesh(solid.mesh ?? buildingMesh(solid.ring, solid.height, solid.base));
      if (solid.mesh) passages.push({ collider, solid });
    }
    for (const panel of built.walkwaySolids) physics.addStaticConvexHull({ vertices: panel.position, friction: 1 });
    for (const deck of built.bridgeSolids) physics.addStaticTrimesh(deck);
  }
  physics.step(FIXED_DT);
  const expected = tiles.flatMap(source => source.buildings.filter(building => building.passages?.length).map(building => building.id));
  assert.deepEqual(passages.map(({ solid }) => solid.id).sort((a, b) => a - b), expected.sort((a, b) => a - b));
  const marinaShells = passages.filter(({ solid }) => solid.id === buildingId);
  assert.equal(marinaShells.length, 1, 'Marina Square has a single passage collider across its tile fragments');
  return { physics, floor, meshes, shell: marinaShells[0].collider };
}

function roofArea(geometry, roofHeight) {
  const positions = geometry.attributes.position.array;
  let sum = 0;
  for (let i = 0; i < positions.length; i += 9) {
    if ([i + 1, i + 4, i + 7].some(y => Math.abs(positions[y] - roofHeight) >= .001)) continue;
    sum += Math.abs(cross([positions[i], positions[i + 2]], [positions[i + 3], positions[i + 5]],
      [positions[i + 6], positions[i + 8]])) / 2;
  }
  return sum;
}

test('Marina Square keeps its original footprint, roof and exterior wall around the two openings', t => {
  const source = { ...tile, buildings: [building] };
  const baseline = buildTile({ ...source, buildings: [uncutBuilding] });
  const after = buildTile(source);
  const material = new MeshBasicMaterial({ side: DoubleSide });
  const previous = new Mesh(baseline.buildings, material), current = new Mesh(after.buildings, material);
  t.after(() => {
    baseline.ground.dispose();
    baseline.buildings.dispose();
    after.ground.dispose();
    after.buildings.dispose();
    material.dispose();
  });
  const [solid] = after.solids;
  assert.deepEqual(solid.ring, baseline.solids[0].ring);
  assert.equal(solid.height, building.height);
  assert.equal(solid.base, undefined);
  assert.ok(Math.abs(roofArea(current.geometry, solid.height) - roofArea(previous.geometry, solid.height)) < .001);
  const physicalTriangles = Array.from(solid.mesh.indices).flatMap(index =>
    [...solid.mesh.vertices.subarray(index * 3, index * 3 + 3)]);
  assert.deepEqual(current.geometry.attributes.position.array, Float32Array.from(physicalTriangles));

  const winding = Math.sign(outline.slice(1).reduce((total, [x, z], i) =>
    total + outline[i][0] * z - x * outline[i][1], 0));
  let unchanged = 0, openings = 0;
  for (let i = 1; i < outline.length; i++) {
    const [a, b] = outline.slice(i - 1, i + 1);
    const { direction } = vector(a, b);
    const dx = winding * direction.z, dz = -winding * direction.x;
    for (const fraction of [.2, .5, .8]) {
      const p = middle(a, b, fraction);
      const [x, z] = p, directionIn = { x: -dx, y: 0, z: -dz };
      const origin = { x: x + .25 * dx, y: 1.4, z: z + .25 * dz };
      const original = paint([previous], origin, directionIn, .35);
      assert.ok(original && Math.abs(original.distance - .25) < .002);
      const changed = paint([current], origin, directionIn, .35);
      if (inside(p, opening)) {
        assert.equal(changed, undefined);
        openings++;
      } else {
        assert.ok(changed && Math.abs(changed.distance - original.distance) < .002);
        unchanged++;
      }
      const lintel = paint([current], { ...origin, y: 5.5 }, directionIn, .35);
      assert.ok(lintel && Math.abs(lintel.distance - .25) < .002);
    }
  }
  assert.ok(openings >= 2 && unchanged > 100);
});

test('both portals and all five lanes are open under a shared rendered and physical 4.5 m soffit', async t => {
  const { physics, floor, meshes, shell } = await buildWorld(t);
  assert.equal(passage.floor, 0);
  assert.equal(passage.soffit, 4.5);
  let roofSamples = 0;
  for (const offset of [-8.45, -6.8, -5.1, -3.4, -1.7, 0, 1.7, 3.4, 5.1, 6.8, 8.45]) {
    const rail = offsetPolyline(route, offset);
    let before = 0, under = 0, after = 0;
    for (let i = 1; i < rail.length; i++) {
      const a = rail[i - 1], b = rail[i], { direction, length } = vector(a, b);
      for (const y of [.04, 1.6, 4.498]) {
        assert.equal(cast(physics, point(a, y), direction, length), null, 'clear forward sweep at ' + offset);
        assert.equal(cast(physics, point(b, y), { x: -direction.x, y: 0, z: -direction.z }, length), null,
          'clear reverse geometry sweep at ' + offset);
      }
      const steps = Math.ceil(length / .3);
      for (let j = 0; j < steps; j++) {
        const p = middle(a, b, (j + .5) / steps);
        const bottom = cast(physics, point(p, 2), down, 3);
        assert.equal(bottom?.collider.handle, floor.handle, 'the stock ground remains inside the passage');
        const floorY = 2 - bottom.timeOfImpact;
        assert.ok(Math.abs(floorY) < .002);
        const asphalt = paint(meshes.ground, point(p, .08), down, .1);
        assert.ok(asphalt && asphalt.point.y >= .029 && asphalt.point.y <= .033, 'the joined pavement covers its full width');
        const ceiling = cast(physics, point(p, .1), up, 12);
        if (inside(p, outline)) {
          assert.equal(after, 0, 'the lane passes through one uninterrupted part of the building');
          assert.equal(ceiling?.collider.handle, shell.handle);
          assert.ok(Math.abs(.1 + ceiling.timeOfImpact - floorY - 4.5) < .002);
          const soffit = paint(meshes.buildings, point(p, .1), up, 12);
          assert.ok(soffit && Math.abs(soffit.point.y - 4.5) < .002);
          assert.ok(soffit.face.normal.y < -.99);
          under++;
        } else {
          assert.notEqual(ceiling?.collider.handle, shell.handle);
          if (under > 0) after++;
          else before++;
        }
      }
    }
    assert.ok(before > 0 && under > 120 && after > 0, 'both ends of each sampled offset remain open to the surface');
    roofSamples += under;
  }
  t.diagnostic(roofSamples + ' matched soffit and pavement probes across the 17 m carriageway');

  const a = route[3], b = route[4];
  const { direction } = vector(a, b);
  for (const t of [.2, .45, .7, .9]) {
    const origin = point(middle(a, b, t), 1.4);
    for (const sign of [-1, 1]) {
      const side = { x: sign * direction.z, y: 0, z: -sign * direction.x };
      const wall = cast(physics, origin, side, 12);
      assert.equal(wall?.collider.handle, shell.handle);
      assert.ok(Math.abs(wall.timeOfImpact - 8.8) < .012, 'the cavity stops at the source-backed shoulder');
      const face = paint(meshes.buildings, origin, side, 12);
      assert.ok(face && Math.abs(face.distance - wall.timeOfImpact) < .002);
      assert.ok(face.face.normal.x * side.x + face.face.normal.z * side.z < -.99, 'cavity normals face the road');
    }
  }
});

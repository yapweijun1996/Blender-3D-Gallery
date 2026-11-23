import assert from 'node:assert/strict';
import test from 'node:test';
import RAPIER from '@dimforge/rapier3d-compat';
import profile from '../scripts/world/fort-canning-tunnel.json' with { type: 'json' };
import { createPhysicsWorld, FIXED_DT } from '../src/world/physics/world.js';
import { installTunnelColliders } from '../src/world/tunnel-prototype/colliders.js';
import { createTunnelGeometry } from '../src/world/tunnel-prototype/geometry.js';

const { sections, surfaces, coveredFrom, coveredTo, clearance } = createTunnelGeometry(profile);
const down = { x: 0, y: -1, z: 0 };
const up = { x: 0, y: 1, z: 0 };
const clamp = (value, min, max) => Math.min(max, Math.max(min, value));
const seams = profile.fragments.slice(1).map(fragment => fragment.points[0].s);

function interpolate(a, b, t) {
  return {
    x: a.x + t * (b.x - a.x), y: a.y + t * (b.y - a.y),
    z: a.z + t * (b.z - a.z), s: a.s + t * (b.s - a.s),
  };
}

function pointAt(s) {
  const next = sections.findIndex(point => point.s > s);
  if (next === 0) return sections[0];
  if (next === -1) return sections.at(-1);
  const [a, b] = [sections[next - 1], sections[next]];
  return { ...interpolate(a, b, (s - a.s) / (b.s - a.s)), tx: a.tx, tz: a.tz };
}

function project(position) {
  let nearest;
  let bestSquared = Infinity;
  for (let i = 1; i < sections.length; i++) {
    const [a, b] = [sections[i - 1], sections[i]];
    const dx = b.x - a.x, dz = b.z - a.z;
    const t = clamp(((position.x - a.x) * dx + (position.z - a.z) * dz) / (dx * dx + dz * dz), 0, 1);
    const point = interpolate(a, b, t);
    const squared = (position.x - point.x) ** 2 + (position.z - point.z) ** 2;
    if (squared < bestSquared) {
      nearest = point;
      bestSquared = squared;
    }
  }
  return { ...nearest, offset: Math.sqrt(bestSquared) };
}

function cast(physics, origin, direction, distance = 12) {
  const hit = physics.world.castRay(new RAPIER.Ray(origin, direction), distance, true);
  assert.ok(hit, `ray at (${origin.x.toFixed(3)}, ${origin.y.toFixed(3)}, ${origin.z.toFixed(3)})`);
  return hit.timeOfImpact;
}

test('open ramps, continuous seam floors, walls and adjacent ground have matching static collision', async () => {
  const physics = await createPhysicsWorld();
  try {
    const sentinel = physics.addGround({ halfWidth: 1, halfDepth: 1 });
    const disposeTunnel = installTunnelColliders(physics, surfaces);
    physics.step(FIXED_DT);
    assert.equal(physics.world.colliders.len(), surfaces.length + 1);

    const rampSample = profile.rampLength / 2;
    for (const s of [rampSample, profile.length - rampSample]) {
      const point = pointAt(s);
      const roadHeight = 2 - cast(physics, { ...point, y: 2 }, down);
      assert.ok(roadHeight < -1 && Math.abs(roadHeight - point.y) < 0.03, 'the open ramp reaches the sloping road');
      for (const sign of [-1, 1]) {
        const offset = sign * (profile.width / 2 + 2);
        const adjacent = { x: point.x + offset * -point.tz, y: 2, z: point.z + offset * point.tx };
        assert.ok(Math.abs(2 - cast(physics, adjacent, down)) < 0.03, 'both sides retain ground at surface level');
      }
    }

    for (const s of seams) {
      for (const offset of [-0.15, 0, 0.15]) {
        const point = pointAt(s + offset);
        assert.ok(Math.abs(1 - cast(physics, { ...point, y: point.y + 1 }, down)) < 0.03, `floor across tile seam ${s}`);
      }
    }

    const middle = pointAt(profile.length / 2);
    const inside = { ...middle, y: middle.y + 1.25 };
    for (const sign of [-1, 1]) {
      const distance = cast(physics, inside, { x: sign * -middle.tz, y: 0, z: sign * middle.tx });
      assert.ok(Math.abs(distance - profile.width / 2) < 0.15, `solid inside wall ${sign}`);
    }
    assert.ok(Math.abs(cast(physics, inside, up) - (clearance - 1.25)) < 0.03, 'ceiling is solid from inside');
    assert.ok(Math.abs(2 - cast(physics, { ...middle, y: 2 }, down)) < 0.03, 'ground closes above the covered section');

    disposeTunnel();
    disposeTunnel();
    physics.step(FIXED_DT);
    assert.equal(physics.world.colliders.len(), 1, 'unloading keeps the other ground collider');
    assert.equal(physics.world.getCollider(sentinel.handle), sentinel);
    assert.equal(physics.world.castRay(new RAPIER.Ray(inside, down), 12, true), null, 'the tunnel floor is no longer solid');
  } finally {
    physics.dispose();
  }
});

test('a sedan drives from the surface through both portals and all three map tiles', async t => {
  const physics = await createPhysicsWorld();
  try {
    installTunnelColliders(physics, surfaces);
    assert.equal(profile.fragments.length, 3);
    const start = pointAt(-16);
    const vehicle = physics.addVehicle({ type: 'sedan', topSpeed: 10,
      position: { x: start.x, y: start.y + 1, z: start.z }, heading: Math.atan2(start.tx, start.tz) });
    for (let i = 0; i < 60; i++) physics.step(FIXED_DT);
    assert.ok(vehicle.getState().wheels.every(wheel => wheel.grounded), 'surface approach supports the parked vehicle');

    const marks = [0, coveredFrom, profile.length / 2, ...seams, coveredTo, profile.length, profile.length + 12];
    const crossings = new Map();
    let minHeight = Infinity, maxOffset = 0, supportedFrames = 0, frames = 0;
    for (; frames < 60 * 80 && crossings.size < marks.length; frames++) {
      const state = vehicle.getState();
      const closest = project(state.position);
      const target = pointAt(closest.s + 8);
      // The test driver supplies ordinary controls. The pose always comes from Rapier.
      const targetHeading = Math.atan2(target.x - state.position.x, target.z - state.position.z);
      const turn = targetHeading - state.heading;
      const steer = clamp(1.6 * Math.atan2(Math.sin(turn), Math.cos(turn)), -1, 1);
      vehicle.setControls({ throttle: 1, steer });
      physics.step(FIXED_DT);
      for (const s of marks) {
        if (closest.s >= s && !crossings.has(s)) crossings.set(s, { state, closest });
      }
      minHeight = Math.min(minHeight, state.position.y);
      maxOffset = Math.max(maxOffset, closest.offset);
      supportedFrames += Number(state.wheels.some(wheel => wheel.grounded));
      assert.ok(state.position.y > closest.y + 0.25 && !state.flipped, `car fell through the road or flipped at ${closest.s.toFixed(2)} m`);
    }

    assert.equal(crossings.size, marks.length, `reached ${[...crossings.keys()]}`);
    assert.ok(maxOffset < profile.width / 2 - 1.4, `maximum lateral offset ${maxOffset.toFixed(3)} m`);
    assert.ok(supportedFrames / frames > 0.98, 'wheel contact persists throughout the ramps and tunnel');
    assert.ok(minHeight < -profile.depth + 1, `the chassis reached ${minHeight.toFixed(3)} m below the surface`);
    for (const [s, { state, closest }] of crossings) {
      assert.ok(closest.s - s < 0.25 && state.wheels[0].grounded && state.wheels[1].grounded, `forward and supported at ${s} m`);
    }
    assert.ok(vehicle.getState().position.y > 0.4, 'the exit rejoins the surface approach');
    assert.ok(vehicle.getState().damage < 0.05, 'ordinary traversal did not hit a wall or obstruction');
    t.diagnostic(`${marks.length} checkpoints in ${(frames * FIXED_DT).toFixed(2)} s, min chassis Y ${minHeight.toFixed(3)} m, max lateral offset ${maxOffset.toFixed(3)} m`);
  } finally {
    physics.dispose();
  }
});

test('both retaining walls stop and damage a sedan, including the downhill bend and covered entrance', async t => {
  const impacts = [
    { label: 'left wall at midpoint', s: profile.length / 2, side: -1, angle: 90 },
    { label: 'right wall at midpoint', s: profile.length / 2, side: 1, angle: 90 },
    { label: 'left wall on downhill bend', s: 48, side: -1, angle: 35 },
    { label: 'left wall at covered entrance', s: coveredFrom - 6, side: -1, angle: 35 },
    { label: 'right wall at covered entrance', s: coveredFrom - 6, side: 1, angle: 35 },
  ];
  for (const { label, s, side, angle } of impacts) {
    const physics = await createPhysicsWorld();
    try {
      installTunnelColliders(physics, surfaces);
      const start = sections.find(section => section.s >= s);
      const heading = Math.atan2(start.tx, start.tz) - side * angle * Math.PI / 180;
      const vehicle = physics.addVehicle({ type: 'sedan', topSpeed: 12,
        position: { x: start.x, y: start.y + 1, z: start.z }, heading });
      vehicle.setControls({ brake: 1 });
      for (let i = 0; i < 60; i++) physics.step(FIXED_DT);

      let maxOffset = 0, minClearance = Infinity;
      vehicle.setControls({ throttle: 1 });
      for (let i = 0; i < 120; i++) {
        physics.step(FIXED_DT);
        const { position } = vehicle.getState();
        const closest = project(position);
        maxOffset = Math.max(maxOffset, closest.offset);
        minClearance = Math.min(minClearance, position.y - closest.y);
      }
      assert.ok(maxOffset > 1 && maxOffset < profile.width / 2, `${label} let the car reach lateral offset ${maxOffset.toFixed(3)} m`);
      assert.ok(minClearance > 0.25, `${label} let the car fall below its road`);
      assert.ok(vehicle.getState().damage > 0, `${label} generated no collision damage`);
      t.diagnostic(`${label}: max lateral offset ${maxOffset.toFixed(3)} m`);
    } finally {
      physics.dispose();
    }
  }
});

test('a failed collider installation releases the colliders already installed', () => {
  const added = [];
  const removed = [];
  let attempts = 0;
  const physics = {
    addStaticTrimesh() {
      if (++attempts === 3) throw new Error('test install failure');
      const collider = { id: attempts };
      added.push(collider);
      return collider;
    },
    removeStatic(collider) { removed.push(collider); },
  };
  assert.throws(() => installTunnelColliders(physics, surfaces), /test install failure/);
  assert.deepEqual(removed, added.toReversed());
});

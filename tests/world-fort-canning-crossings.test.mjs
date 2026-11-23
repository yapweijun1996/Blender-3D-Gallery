import assert from "node:assert/strict";
import test from "node:test";
import profile from "../scripts/world/fort-canning-integration.json" with { type: "json" };
import { createPhysicsWorld, FIXED_DT } from "../src/world/physics/world.js";
import { createStreamedTunnelGround } from "../src/world/tunnel-integration/colliders.js";
import { surfaceBounds } from "../src/world/tunnel-integration/ground.js";
import { createTunnelGeometry, nearestTunnelSection } from "../src/world/tunnel-prototype/geometry.js";

const crossingIds = ["430502717:0", "646730739:0"];
const clamp = (value, low, high) => Math.max(low, Math.min(high, value));
const geometry = createTunnelGeometry(profile);
const bounds = surfaceBounds(geometry.surfaces.find(surface => surface.id === "terrain"));

function surfaceSections(points) {
  let s = 0;
  return points.map(([x, z], index) => {
    if (index) s += Math.hypot(x - points[index - 1][0], z - points[index - 1][1]);
    return { x, y: 0, z, s };
  });
}

function sample(sections, station) {
  const end = sections.at(-1).s;
  const s = clamp(station, sections[0].s, end);
  const next = sections.findIndex(point => point.s > s);
  const index = next < 0 ? sections.length - 1 : next;
  const a = sections[index - 1], b = sections[index];
  const t = (s - a.s) / (b.s - a.s);
  return {
    x: a.x + (b.x - a.x) * t,
    y: a.y + (b.y - a.y) * t,
    z: a.z + (b.z - a.z) * t,
    heading: Math.atan2(b.x - a.x, b.z - a.z),
  };
}

function addSedan(physics, sections, start, crossing, finish) {
  const { x, y, z, heading } = sample(sections, start);
  const car = physics.addVehicle({ type: "sedan", topSpeed: 7, position: { x, y: y + 1, z }, heading });
  car.setControls({ brake: 1 });
  return { car, sections, crossing, finish, crossed: false, ended: false, maxLateral: 0 };
}

function drive(driver) {
  const state = driver.car.getState();
  const nearest = nearestTunnelSection(driver.sections, state.position);
  const target = sample(driver.sections, nearest.s + 5);
  const headingError = Math.atan2(target.x - state.position.x, target.z - state.position.z) - state.heading;
  const turn = Math.atan2(Math.sin(headingError), Math.cos(headingError));
  driver.crossed ||= nearest.s > driver.crossing;
  driver.ended ||= nearest.s > driver.finish;
  driver.maxLateral = Math.max(driver.maxLateral, Math.abs(nearest.lateral));
  assert.ok(!state.flipped && state.position.y > nearest.y + .25 && state.position.y < nearest.y + 1.15,
    `expected support near station ${nearest.s.toFixed(2)} m, chassis at Y=${state.position.y.toFixed(3)} m`);
  if (driver.ended) driver.car.setControls({ brake: 1 });
  else driver.car.setControls({ throttle: 1, steer: clamp(2 * turn, -1, 1) });
  return state;
}

test("a sedan takes the extended approach, both portals and every affected tile seam", async t => {
  const physics = await createPhysicsWorld();
  const ground = createStreamedTunnelGround(physics, { bounds, surfaces: geometry.surfaces });
  try {
    ground.setActive(true);
    const finish = profile.length - 2;
    const driver = addSedan(physics, geometry.sections, -15, geometry.coveredFrom, finish);
    for (let step = 0; step < 90; step++) physics.step(FIXED_DT);
    const checkpoints = [0, geometry.coveredFrom, ...profile.fragments.slice(1).map(tile => tile.points[0].s), geometry.coveredTo, finish];
    const visited = new Set();
    let minHeight = Infinity, supported = 0, frames = 0;
    for (; frames < 60 * 110 && !driver.ended; frames++) {
      const state = drive(driver);
      const station = nearestTunnelSection(geometry.sections, state.position).s;
      for (const mark of checkpoints) if (station >= mark) visited.add(mark);
      minHeight = Math.min(minHeight, state.position.y);
      supported += Number(state.wheels.some(wheel => wheel.grounded));
      physics.step(FIXED_DT);
    }
    assert.ok(driver.ended && checkpoints.every(point => visited.has(point)), "the sedan reached every portal and tile seam");
    assert.ok(minHeight < -4.7 && driver.car.getState().position.y > .4, "the sedan drove down to the bore and back up");
    assert.ok(supported / frames > .98 && driver.car.getState().damage < .05, "wheel support persisted without a collision");
    assert.ok(driver.maxLateral < profile.width / 2 - .9);
    t.diagnostic(`${(frames * FIXED_DT).toFixed(2)} simulated s, minimum chassis Y ${minHeight.toFixed(3)} m`);
  } finally {
    ground.dispose();
    physics.dispose();
  }
});

for (const edgeId of crossingIds) {
  test(`sedans pass simultaneously at both levels of mapped crossing ${edgeId}`, async t => {
    const crossing = profile.crossings.find(item => item.kind === "road" && item.edgeId === edgeId && item.at);
    assert.ok(crossing?.roofCovered, "the fixture covers the full swept width of the surface road");
    const upperSections = surfaceSections(crossing.points);
    const upperStation = nearestTunnelSection(upperSections, crossing.at).s;
    const radius = Math.min(16, upperStation - 1, upperSections.at(-1).s - upperStation - 1);
    assert.ok(radius > 5, "there is a mapped surface approach and exit");

    const physics = await createPhysicsWorld();
    const ground = createStreamedTunnelGround(physics, { bounds, surfaces: geometry.surfaces });
    try {
      ground.setActive(true);
      const lower = addSedan(physics, geometry.sections, crossing.at.s - radius, crossing.at.s, crossing.at.s + radius * .7);
      const upper = addSedan(physics, upperSections, upperStation - radius, upperStation, upperStation + radius * .7);
      for (let step = 0; step < 90; step++) physics.step(FIXED_DT);
      let minPlanarSeparation = Infinity, verticalAtClosest = 0;
      for (let step = 0; step < 60 * 12 && !(upper.ended && lower.ended); step++) {
        const below = drive(lower), above = drive(upper);
        const horizontal = Math.hypot(above.position.x - below.position.x, above.position.z - below.position.z);
        if (horizontal < minPlanarSeparation) {
          minPlanarSeparation = horizontal;
          verticalAtClosest = above.position.y - below.position.y;
        }
        physics.step(FIXED_DT);
      }
      assert.ok(upper.crossed && lower.crossed && upper.ended && lower.ended, "both cars drove across and left the crossing");
      assert.ok(minPlanarSeparation < 2.5, `paths came within ${minPlanarSeparation.toFixed(2)} m on plan`);
      assert.ok(verticalAtClosest > 4.9, `crossing held ${verticalAtClosest.toFixed(2)} m of separation`);
      assert.ok(upper.maxLateral < crossing.width / 2 - .7, "the upper car stayed within the measured roadway");
      assert.ok(lower.maxLateral < profile.width / 2 - .9, "the lower car stayed within the tunnel");
      assert.ok(upper.car.getState().damage < .05 && lower.car.getState().damage < .05, "the cars did not collide across levels");
      t.diagnostic(`closest plan separation ${minPlanarSeparation.toFixed(2)} m, vertical separation ${verticalAtClosest.toFixed(2)} m`);
    } finally {
      ground.dispose();
      physics.dispose();
    }
  });
}

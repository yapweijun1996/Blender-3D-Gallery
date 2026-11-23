import assert from "node:assert/strict";
import test from "node:test";
import RAPIER from "@dimforge/rapier3d-compat";
import profile from "../scripts/world/fort-canning-integration.json" with { type: "json" };
import { VEHICLE_TYPES } from "../src/world/physics/vehicle.js";
import { createPhysicsWorld, FIXED_DT } from "../src/world/physics/world.js";
import { createStreamedTunnelGround } from "../src/world/tunnel-integration/colliders.js";
import { createFortCanningMergeGeometry } from "../src/world/tunnel-integration/merge-geometry.js";
import { nearestTunnelSection } from "../src/world/tunnel-prototype/geometry.js";

const clamp = (value, min, max) => Math.max(min, Math.min(max, value));

function sample(lane, station) {
  const s = clamp(station, lane[0].s, lane.at(-1).s);
  const next = lane.findIndex(point => point.s > s);
  const index = next < 0 ? lane.length - 1 : next;
  const a = lane[index - 1], b = lane[index];
  const t = (s - a.s) / (b.s - a.s);
  return {
    x: a.x + (b.x - a.x) * t,
    y: a.y + (b.y - a.y) * t,
    z: a.z + (b.z - a.z) * t,
    heading: Math.atan2(b.x - a.x, b.z - a.z),
  };
}

function crossingStation(lane, road) {
  // Intersect the actual lane center with the pinned surface road centerline.
  for (let i = 1; i < lane.length; i++) {
    const a = lane[i - 1], b = lane[i];
    const dx = b.x - a.x, dz = b.z - a.z;
    for (let j = 1; j < road.length; j++) {
      const [x, z] = road[j - 1];
      const ex = road[j][0] - x, ez = road[j][1] - z;
      const det = dx * ez - dz * ex;
      if (Math.abs(det) < 1e-8) continue;
      const t = ((x - a.x) * ez - (z - a.z) * ex) / det;
      const u = ((x - a.x) * dz - (z - a.z) * dx) / det;
      if (t >= 0 && t <= 1 && u >= 0 && u <= 1) return a.s + (b.s - a.s) * t;
    }
  }
  assert.fail("the Link lane should cross the actual Fort Canning Road centerline");
}

function addSedan(physics, lane, start, seam) {
  const initial = sample(lane, start);
  const car = physics.addVehicle({ type: "sedan", topSpeed: 7, heading: initial.heading,
    position: { x: initial.x, y: initial.y + 1, z: initial.z } });
  car.setControls({ brake: 1 });
  return { car, lane, seam, start, finished: false, seamFrames: 0, maxOffset: 0, maxStation: start };
}

function drive(driver, active) {
  const state = driver.car.getState();
  const nearest = nearestTunnelSection(driver.lane, state.position);
  const offset = nearest.s - driver.seam;
  const lift = state.position.y - nearest.y;
  assert.ok(!state.flipped && lift > .25 && lift < 1.15,
    `wrong deck at ${offset.toFixed(2)} m from seam: chassis ${state.position.y.toFixed(3)} m, route ${nearest.y.toFixed(3)} m`);
  if (Math.abs(offset) < 4) {
    assert.ok(state.wheels.every(wheel => wheel.grounded), `all wheels are supported across seam at ${offset.toFixed(2)} m`);
    driver.seamFrames++;
  }
  if (offset > 18) driver.finished = true;
  driver.maxOffset = Math.max(driver.maxOffset, Math.abs(nearest.lateral));
  driver.maxStation = Math.max(driver.maxStation, nearest.s);
  if (!active || driver.finished) driver.car.setControls({ brake: 1 });
  else {
    const aim = sample(driver.lane, nearest.s + 4);
    const turn = Math.atan2(aim.x - state.position.x, aim.z - state.position.z) - state.heading;
    driver.car.setControls({ throttle: 1, steer: clamp(2.4 * Math.atan2(Math.sin(turn), Math.cos(turn)), -1, 1) });
  }
  return { state, offset };
}

function assertNoChassisContact(physics, driver) {
  const collider = driver.car.collider;
  physics.world.contactPairsWith(collider, other => {
    physics.world.contactPair(collider, other, manifold => {
      for (let i = 0; i < manifold.numContacts(); i++) {
        assert.ok(manifold.contactDist(i) > 0, `chassis contacted collider ${other.handle}`);
      }
    });
  });
}

test("Rapier sedans use adjacent feeder lanes and merge onto the same level of Penang Road", async t => {
  const { surfaces, bounds, lanes, seam } = createFortCanningMergeGeometry(profile);
  const fortCanningRoad = profile.crossings.find(item => item.edgeId === "646730739:0");
  assert.ok(fortCanningRoad, "the route fixture contains Fort Canning Road");
  const crossing = crossingStation(lanes.link, fortCanningRoad.points);
  const atCrossing = sample(lanes.link, crossing);
  assert.ok(atCrossing.y <= -4.9, "the driven lane keeps the full roof envelope at Fort Canning Road");
  const seamPoint = lane => {
    const through = lane.filter(point => Math.abs((point.x - seam.x) * seam.tx + (point.z - seam.z) * seam.tz) < 1e-5);
    assert.equal(through.length, 1, "a lane has exactly one vertex in the common seam plane");
    assert.ok(Math.abs(through[0].y - seam.y) < 1e-6, "the lane meets the expected seam level");
    return through[0];
  };
  const linkJoin = seamPoint(lanes.link), penangJoin = seamPoint(lanes.penang);
  assert.ok(Math.abs(Math.hypot(linkJoin.x - penangJoin.x, linkJoin.z - penangJoin.z) - profile.laneWidth) < 1e-6,
    "the two driven lane centers are adjacent at the seam");
  const physics = await createPhysicsWorld();
  const ground = createStreamedTunnelGround(physics, { bounds, surfaces });
  try {
    ground.setActive(true);
    const link = addSedan(physics, lanes.link, crossing - 16, linkJoin.s);
    const penang = addSedan(physics, lanes.penang, lanes.penang[0].s + 4, penangJoin.s);
    for (let step = 0; step < 90; step++) physics.step(FIXED_DT);
    const { x, y, z } = atCrossing;
    const belowRoof = new RAPIER.Ray({ x, y: y + 1, z }, { x: 0, y: 1, z: 0 });
    const aboveRoad = new RAPIER.Ray({ x, y: 2, z }, { x: 0, y: -1, z: 0 });
    const roof = physics.world.castRay(belowRoof, 10, true);
    const road = physics.world.castRay(aboveRoad, 10, true);
    assert.ok(roof && Math.abs(roof.timeOfImpact + 1 - profile.simulation.clearance) < .03,
      "the exact crossing has a collidable roof above the Link lane");
    assert.ok(road && Math.abs(road.timeOfImpact - 2) < .03, "Fort Canning Road still has ground-level support");
    const surfaceChassisY = penang.car.getState().position.y;
    const penangRunway = penang.seam - penang.start;
    let penangStarted = false, crossingHeight, frames = 0;
    let nearestCars = Infinity;
    for (; frames < 60 * 48 && !(link.finished && penang.finished); frames++) {
      const below = drive(link, true);
      const linkStation = below.offset + link.seam;
      if (Math.abs(linkStation - crossing) < .15) crossingHeight = below.state.position.y;
      // Release the parked Penang car slightly early so both cars arrive together.
      penangStarted ||= -below.offset < penangRunway + 3;
      const upper = drive(penang, penangStarted);
      if (Math.abs(below.offset) < 8 && Math.abs(upper.offset) < 8 && below.state.speed > 2 && upper.state.speed > 2) {
        const a = below.state.position, b = upper.state.position;
        nearestCars = Math.min(nearestCars, Math.hypot(a.x - b.x, a.z - b.z));
      }
      physics.step(FIXED_DT);
      assertNoChassisContact(physics, link);
      assertNoChassisContact(physics, penang);
    }
    assert.ok(link.finished && penang.finished,
      `both cars must leave the seam: Link ${(link.maxStation - link.seam).toFixed(2)} m, Penang ${(penang.maxStation - penang.seam).toFixed(2)} m`);
    assert.ok(nearestCars < 4.5, "both cars must drive side by side at the merge during the same run");
    assert.ok(crossingHeight < -4.1, "the Link car reached the actual crossing on the lower deck");
    const laneMargin = profile.laneWidth / 2 - VEHICLE_TYPES.sedan.chassisHalfExtents.x;
    for (const driver of [link, penang]) {
      assert.ok(driver.seamFrames > 45, "the car did not skip the wheel-support assertion at the seam");
      assert.ok(driver.maxOffset < laneMargin, `the car remained within its assigned lane (offset ${driver.maxOffset.toFixed(3)} m)`);
      assert.ok(driver.car.getState().damage < .01, "no chassis damage on either route");
      assert.ok(Math.abs(driver.car.getState().position.y - surfaceChassisY) < .1, "both routes finish on the same surface level");
    }
    t.diagnostic(`${(frames * FIXED_DT).toFixed(2)} simulated s, closest cars ${nearestCars.toFixed(2)} m, Link chassis Y ${crossingHeight.toFixed(3)} m at Fort Canning Road`);
  } finally {
    ground.dispose();
    physics.dispose();
  }
});

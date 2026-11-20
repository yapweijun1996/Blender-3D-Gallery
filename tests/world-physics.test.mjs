import assert from "node:assert/strict";
import test from "node:test";
import { createPhysicsWorld } from "../src/world/physics/world.js";

const run = (physics, seconds) => { for (let i = 0; i < seconds * 60; i++) physics.step(1 / 60); };

async function scene(type = "hatchback") {
  const physics = await createPhysicsWorld();
  physics.addGround({});
  const vehicle = physics.addVehicle({ type });
  return { physics, vehicle };
}

test("a car settles on its wheels and accelerates forward", async () => {
  const { physics, vehicle } = await scene();
  run(physics, 1);
  assert.ok(vehicle.getState().wheels.every(wheel => wheel.grounded));
  vehicle.setControls({ throttle: 1 });
  for (let i = 0; i < 300; i++) { vehicle.setControls({ throttle: 1 }); physics.step(1 / 60); }
  const state = vehicle.getState();
  assert.ok(state.forwardSpeed > 8, `speed ${state.forwardSpeed}`);
  assert.ok(state.position.z > 10);
  assert.equal(state.flipped, false);
  physics.dispose();
});

test("positive steer turns the heading to the left (towards +X)", async () => {
  const { physics, vehicle } = await scene();
  for (let i = 0; i < 360; i++) { vehicle.setControls({ throttle: i < 200 ? 1 : 0.3, steer: i > 120 ? 0.5 : 0 }); physics.step(1 / 60); }
  assert.ok(vehicle.getState().heading > 0.15, `heading ${vehicle.getState().heading}`);
  physics.dispose();
});

test("braking stops the car", async () => {
  const { physics, vehicle } = await scene();
  for (let i = 0; i < 240; i++) { vehicle.setControls({ throttle: 1 }); physics.step(1 / 60); }
  for (let i = 0; i < 360; i++) { vehicle.setControls({ brake: 1 }); physics.step(1 / 60); }
  assert.ok(vehicle.getState().speed < 0.5);
  physics.dispose();
});

test("hitting a wall at speed damages the car", async () => {
  const { physics, vehicle } = await scene("sedan");
  physics.addStaticBox({ halfExtents: { x: 10, y: 2, z: 0.5 }, position: { x: 0, y: 2, z: 60 } });
  for (let i = 0; i < 900; i++) { vehicle.setControls({ throttle: 1 }); physics.step(1 / 60); }
  const state = vehicle.getState();
  assert.ok(state.damage > 0.1, `damage ${state.damage}`);
  assert.ok(state.position.z < 60, "car stayed in front of the wall");
  physics.dispose();
});

test("a car lying on its roof is reported flipped and can be reset upright", async () => {
  const { physics, vehicle } = await scene("hatchback");
  run(physics, 1);
  const { x, y, z } = vehicle.body.translation();
  vehicle.body.setTranslation({ x, y: y + 1, z }, true);
  vehicle.body.setRotation({ x: 0, y: 0, z: 1, w: 0 }, true); // upside down
  run(physics, 4);
  assert.equal(vehicle.getState().flipped, true);
  vehicle.resetUpright({ repair: true });
  run(physics, 1.5);
  const state = vehicle.getState();
  assert.equal(state.flipped, false);
  assert.equal(state.damage, 0);
  assert.ok(state.wheels.every(wheel => wheel.grounded));
  physics.dispose();
});

test("every vehicle type spawns, settles and drives", async () => {
  for (const type of ["hatchback", "sedan", "van", "bus", "lorry", "motorbike"]) {
    const { physics, vehicle } = await scene(type);
    for (let i = 0; i < 300; i++) { vehicle.setControls({ throttle: 1 }); physics.step(1 / 60); }
    const state = vehicle.getState();
    assert.ok(state.forwardSpeed > 3, `${type} speed ${state.forwardSpeed}`);
    assert.equal(state.flipped, false, type);
    physics.dispose();
  }
});

test("reverse pushes the car backwards from a standstill", async () => {
  const { physics, vehicle } = await scene();
  run(physics, 1);
  for (let i = 0; i < 240; i++) { vehicle.setControls({ reverse: 1 }); physics.step(1 / 60); }
  const state = vehicle.getState();
  assert.ok(state.forwardSpeed < -2, `speed ${state.forwardSpeed}`);
  assert.ok(state.forwardSpeed > -8);
  physics.dispose();
});

test("crash damage grows with speed: a bump is small, a fast hit is serious but not total", async () => {
  const damageAt = async target => {
    const physics = await createPhysicsWorld();
    physics.addGround({});
    physics.addStaticBox({ halfExtents: { x: 10, y: 2, z: 0.5 }, position: { x: 0, y: 2, z: 80 } });
    const car = physics.addVehicle({ type: "sedan", topSpeed: 28, position: { x: 0, y: 1, z: 0 } });
    for (let i = 0; i < 60 * 12; i++) { car.setControls({ throttle: car.getState().speed < target ? 1 : 0 }); physics.step(1 / 60); }
    const damage = car.getState().damage;
    physics.dispose();
    return damage;
  };
  const slow = await damageAt(8), medium = await damageAt(14), fast = await damageAt(22);
  assert.ok(slow > 0 && slow < 0.2, `29 km/h: ${slow}`);
  assert.ok(medium > slow && fast > medium, "more speed, more damage");
  assert.ok(fast > 0.3 && fast < 0.7, `79 km/h: ${fast}`);
});

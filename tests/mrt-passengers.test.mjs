import assert from "node:assert/strict";
import test from "node:test";
import { DOORWAYS, passengerPose, roleOf } from "../src/mrt/passengers.js";
import { CYCLE, CYCLE_SECONDS, trainState } from "../src/mrt/schedule.js";

test("each doorway has one person boarding and one getting off, swapping every cycle", () => {
  for (let cycle = 0; cycle < 4; cycle++) {
    for (let door = 0; door < DOORWAYS.length; door++) {
      const roles = [roleOf(door * 2, cycle), roleOf(door * 2 + 1, cycle)].sort();
      assert.deepEqual(roles, ["alighting", "boarding"]);
    }
  }
  assert.notEqual(roleOf(0, 0), roleOf(0, 1));
});

test("nobody is on the track side of the screen doors unless the doors are open", () => {
  for (let clock = 0; clock < CYCLE_SECONDS * 3; clock += 0.1) {
    const doors = trainState(clock).doors;
    for (let i = 0; i < DOORWAYS.length * 2; i++) {
      const pose = passengerPose(i, clock);
      if (pose.visible && pose.z > 2.2) assert.ok(doors > 0.99, `person ${i} at z=${pose.z.toFixed(2)} with doors ${doors} at t=${clock.toFixed(1)}`);
      assert.ok(Number.isFinite(pose.x) && Number.isFinite(pose.z));
    }
  }
});

test("a boarder walks to the door and disappears into the train; an alighter steps out and walks away", () => {
  const boarder = [0, 1].find(i => roleOf(i, 0) === "boarding"), alighter = 1 - boarder;
  assert.equal(passengerPose(boarder, 1).visible, true);
  assert.equal(passengerPose(boarder, 1).clip, "idle");
  assert.equal(passengerPose(boarder, CYCLE.arrive + CYCLE.open + 5).visible, false);
  assert.equal(passengerPose(alighter, 1).visible, false);
  const out = passengerPose(alighter, CYCLE.arrive + CYCLE.open + 5);
  assert.ok(out.visible && out.clip === "walk" && out.z < 1);
  assert.equal(passengerPose(alighter, CYCLE.arrive + CYCLE.open + 12).visible, false);
});

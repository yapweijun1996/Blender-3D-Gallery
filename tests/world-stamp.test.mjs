import assert from "node:assert/strict";
import test from "node:test";
import { STAMP_ZONE, createStamp } from "../src/world/stamp.js";

test("the passport is shown first, then the marker sweeps and a press inside the zone stamps", () => {
  const stamp = createStamp();
  assert.equal(stamp.state.phase, "show");
  stamp.update(1);
  assert.equal(stamp.state.value, 0, "the marker does not move before the passport is shown");
  assert.equal(stamp.press(), "shown");
  assert.equal(stamp.state.phase, "stamp");
  let hit = null;
  for (let step = 0; step < 600 && !hit; step++) {
    stamp.update(1 / 60);
    const inside = stamp.state.value >= STAMP_ZONE[0] && stamp.state.value <= STAMP_ZONE[1];
    if (inside) hit = stamp.press();
  }
  assert.equal(hit, "hit");
  assert.equal(stamp.state.phase, "done");
  assert.equal(stamp.press(), "ignored");
});

test("a press outside the zone is a miss and the game goes on", () => {
  const stamp = createStamp();
  stamp.press();
  assert.equal(stamp.press(), "miss", "the marker starts at the left end, outside the zone");
  assert.equal(stamp.state.phase, "stamp");
});

test("the marker bounces between the two ends of the bar", () => {
  const stamp = createStamp();
  stamp.press();
  let reachedEnd = false, cameBack = false;
  for (let step = 0; step < 600; step++) {
    stamp.update(1 / 60);
    if (stamp.state.value === 1) reachedEnd = true;
    if (reachedEnd && stamp.state.value < 0.9) cameBack = true;
  }
  assert.ok(reachedEnd && cameBack);
  assert.ok(stamp.state.value >= 0 && stamp.state.value <= 1);
});

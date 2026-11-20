import assert from "node:assert/strict";
import fs from "node:fs";
import { Color, Scene } from "three";
import test from "node:test";
import { createSignalLights, signalApproaches } from "../src/world/signals.js";
import { buildTrafficGraph } from "../src/world/traffic.js";

const tiles = [];
for (let z = -2; z <= 2; z++) for (let x = -2; x <= 2; x++) {
  const file = `models/world/tiles/${x}_${z}.json`;
  if (fs.existsSync(file)) tiles.push(JSON.parse(fs.readFileSync(file, "utf8")));
}

test("signalised junctions get poles on the verge of each approach", () => {
  const graph = buildTrafficGraph(tiles);
  const approaches = signalApproaches(graph);
  assert.ok(approaches.length >= 8, `${approaches.length} approaches`);
  for (const item of approaches) {
    assert.ok(Number.isFinite(item.x) && Number.isFinite(item.z));
    assert.ok(Math.abs(Math.hypot(item.dx, item.dz) - 1) < 1e-6);
    assert.ok(item.phase === 0 || item.phase === 1);
  }
});

test("lamps show one colour per approach and follow the state", () => {
  const scene = new Scene();
  const lights = createSignalLights(scene, 8);
  lights.setApproaches([{ x: 0, z: 0, dx: 0, dz: 1, phase: 1 }, { x: 10, z: 0, dx: 1, dz: 0, phase: 0 }]);
  assert.equal(lights.count, 2);
  lights.update((dx, dz) => (dz ? "red" : "green"));
  const lamps = lights.meshes[2];
  const read = index => { const target = new Color(); lamps.getColorAt(index, target); return target; };
  assert.ok(read(0).r > 0.9 && read(0).g < 0.2, "first approach: red lamp lit");
  assert.ok(read(1).r < 0.1 && read(1).g < 0.1, "first approach: amber lamp off");
  assert.ok(read(5).g > 0.5 && read(5).r < 0.1, "second approach: green lamp lit");
  lights.dispose();
});

import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import { LINKS, MODULES, VIEW_YAW, linkSegments, onPlinth, placements } from "../src/commerce-hub/layout.js";

test("each module is rotated from the camera azimuth it was modelled for", () => {
  for (const { id, yaw } of MODULES) {
    const report = JSON.parse(fs.readFileSync(`models/commerce-hub/reports/${id}.json`, "utf8"));
    assert.ok(Math.abs(report.render.camera_rotation_rad[2] * 180 / Math.PI - yaw) < 0.05, id);
  }
});

test("placements turn every module towards the shared camera", () => {
  for (const place of placements()) {
    const report = JSON.parse(fs.readFileSync(`models/commerce-hub/reports/${place.id}.json`, "utf8"));
    const modelled = report.render.camera_rotation_rad[2] * 180 / Math.PI;
    assert.ok(Math.abs(place.rotation * 180 / Math.PI - (VIEW_YAW - modelled)) < 0.05, place.id);
  }
});

test("every module keeps its traced width", () => {
  for (const [place, module] of placements().map((place, i) => [place, MODULES[i]])) {
    assert.ok(place.scale > 0.4 && place.scale < 1.3, place.id);
    assert.ok(place.content.length === 2 && place.content.every(value => value > 0.5 && value <= 1), place.id);
  }
});

test("links join known modules with segments between their edges", () => {
  const ids = new Set(MODULES.map(module => module.id));
  assert.equal(ids.size, 7);
  assert.equal(LINKS.length, 8);
  for (const [from, to] of LINKS) assert.ok(ids.has(from) && ids.has(to));
  for (const { points } of linkSegments()) {
    const [a, b] = [points[0], points.at(-1)];
    assert.ok(Math.hypot(b[0] - a[0], b[1] - a[1]) > 0.3);
  }
  for (const place of placements()) assert.ok(place.scale > 0 && Number.isFinite(place.x + place.z + place.rotation));
});

test("each link node sits on its module's plinth edge", () => {
  const places = new Map(placements().map(place => [place.id, place]));
  for (const { from, to, node, nodeModule } of linkSegments()) {
    assert.ok(onPlinth(places.get(nodeModule), node, 0.3), `${from}-${to} node reaches ${nodeModule}`);
    assert.ok(!onPlinth(places.get(nodeModule), node, -0.45), `${from}-${to} node is not inside ${nodeModule}`);
  }
});

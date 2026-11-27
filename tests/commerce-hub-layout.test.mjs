import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import { LINKS, MODULES, VIEW_YAW, linkSegments, placements } from "../src/commerce-hub/layout.js";

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

test("links join known modules with segments between their edges", () => {
  const ids = new Set(MODULES.map(module => module.id));
  assert.equal(ids.size, 7);
  assert.equal(LINKS.length, 8);
  for (const [from, to] of LINKS) assert.ok(ids.has(from) && ids.has(to));
  for (const { a, b } of linkSegments()) assert.ok(Math.hypot(b[0] - a[0], b[1] - a[1]) > 0.3);
  for (const place of placements()) assert.ok(place.scale > 0 && Number.isFinite(place.x + place.z + place.rotation));
});

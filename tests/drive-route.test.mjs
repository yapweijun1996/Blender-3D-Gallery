import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import { buildRoute, findRoad, locate, project, roadAt, sample, tripHour } from "../src/drive/route.js";

const data = JSON.parse(readFileSync(new URL("../models/drive/route-mbs-jb.json", import.meta.url), "utf8"));
const route = buildRoute(data);

test("route data keeps its licence note and a plausible length", () => {
  assert.match(data.source, /OpenStreetMap/);
  assert.ok(data.coordinates.length > 500);
  assert.ok(route.length > 30_000 && route.length < 33_000, `route length ${route.length}`);
});

test("projection puts north up and Johor north-west of Marina Bay", () => {
  const [x0, z0] = project([103.8607, 1.2834]);
  assert.ok(Math.abs(x0) < 1e-6 && Math.abs(z0) < 1e-6);
  const [x, z] = project([103.7746, 1.4986]);
  assert.ok(z < -20_000 && x < -8_000);
});

test("resampled route is evenly spaced and its headings are continuous", () => {
  for (let i = 2; i < route.points.length - 2; i++) {
    const gap = route.points[i].s - route.points[i - 1].s;
    assert.ok(gap > 0 && gap < route.spacing * 1.01 + 1e-6, `gap ${gap} at ${i}`);
  }
  let worst = 0;
  for (let i = 1; i < route.points.length; i++) {
    let turn = Math.abs(route.points[i].heading - route.points[i - 1].heading);
    turn = Math.min(turn, 2 * Math.PI - turn);
    worst = Math.max(worst, turn);
  }
  assert.ok(worst < 1.7, `sharpest turn between samples ${worst}`);
});

test("sample, locate and offsets agree", () => {
  const d = 12_345;
  const centre = sample(route, d);
  const left = sample(route, d, 3.5);
  assert.ok(Math.abs(Math.hypot(left.x - centre.x, left.z - centre.z) - 3.5) < 1e-6);
  const found = locate(route, centre.x, centre.z, d - 50);
  assert.ok(Math.abs(found.distance - d) <= route.spacing && found.off < 6);
  const side = locate(route, left.x, left.z, d);
  assert.ok(Math.abs(Math.abs(side.lateral) - 3.5) < 1.5);
  assert.ok(Math.abs(sample(route, -5).heading - route.points[0].heading) < 1e-9, "before the start the pose is the start pose");
  assert.ok(sample(route, 1e9).index >= route.points.length - 3, "past the end the pose is the last segment");
});

test("named roads follow the trip order and the border sits near the Causeway", () => {
  assert.match(roadAt(route, 100).name, /Sheares/);
  assert.match(roadAt(route, route.length - 10).name, /Southkey/);
  const checkpoint = findRoad(route, "Woodlands border checkpoint"), causeway = findRoad(route, "Causeway"), ciq = findRoad(route, "JB CIQ");
  assert.ok(checkpoint < causeway && causeway < ciq);
  const at = sample(route, causeway);
  const [, zc] = project([103.7678, 1.4437]);
  assert.ok(Math.abs(at.z - zc) < 800, "Causeway start is within 800 m of the real crossing");
  assert.ok(tripHour(route, 0) < tripHour(route, route.length));
});

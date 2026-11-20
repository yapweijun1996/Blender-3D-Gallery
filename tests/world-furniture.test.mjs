import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";
import { busStopPlacements, lampPlacements, nearestRoad } from "../src/world/furniture.js";
import { buildTrafficGraph } from "../src/world/traffic.js";

const tiles = [];
for (let z = -2; z <= 2; z++) for (let x = -2; x <= 2; x++) {
  const file = `models/world/tiles/${x}_${z}.json`;
  if (fs.existsSync(file)) tiles.push(JSON.parse(fs.readFileSync(file, "utf8")));
}
const graph = buildTrafficGraph(tiles);

test("street lamps stand on the verge beside the road, not on it", () => {
  const lamps = lampPlacements(graph);
  assert.ok(lamps.length > 50, `${lamps.length} lamps`);
  for (const lamp of lamps.slice(0, 200)) {
    const road = nearestRoad(graph, lamp.x, lamp.z);
    assert.ok(road.distance > 1.5, `lamp ${road.distance} m from a road centre line`);
  }
  assert.ok(lamps.every(lamp => Number.isFinite(lamp.yaw)));
});

test("bus stops get a shelter and a flag next to the road, facing it", () => {
  const stops = tiles.flatMap(tile => tile.busStops.map(stop => [stop.point[0] + tile.x * 250, stop.point[1] + tile.z * 250]));
  assert.ok(stops.length > 5);
  const { shelters, flags } = busStopPlacements(graph, stops);
  assert.ok(shelters.length > 3);
  assert.equal(shelters.length, flags.length);
  let facingRoad = 0, clear = 0;
  for (const shelter of shelters) {
    const road = nearestRoad(graph, shelter.x, shelter.z);
    if (road.distance >= road.edge.width / 2 + 1.5) clear++;
    // Facing the road: +Z after the yaw points to the nearest road point.
    const facing = [Math.sin(shelter.yaw), Math.cos(shelter.yaw)];
    const toRoad = [road.x - shelter.x, road.z - shelter.z];
    if (facing[0] * toRoad[0] + facing[1] * toRoad[1] > 0) facingRoad++;
  }
  // A stop at a junction can sit nearer to a side road than to the road it serves, so most face the nearest road (a stop on a dual carriageway may be nearer the opposite carriageway).
  assert.ok(clear / shelters.length > 0.6, `${clear} of ${shelters.length} are clear of the carriageway`);
  assert.ok(facingRoad / shelters.length > 0.6, `${facingRoad} of ${shelters.length} face the road`);
});

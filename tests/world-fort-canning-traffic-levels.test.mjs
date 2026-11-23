import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import profile from "../scripts/world/fort-canning-integration.json" with { type: "json" };
import { readFortCanningJunction } from "../scripts/world/fort-canning-junction.mjs";
import { buildTrafficGraph, createTraffic, heightOnEdge, sampleEdge, VEHICLE_TYPES } from "../src/world/traffic.js";
import { createFortCanningMergeAlignment } from "../src/world/tunnel-integration/merge-alignment.js";
import { fortCanningTrafficRoads } from "../src/world/tunnel-integration/traffic-roads.js";

const base = profile.source.tiles.map(({ key }) =>
  JSON.parse(readFileSync(new URL("../models/world/tiles/" + key + ".json", import.meta.url))));
const witness = await readFortCanningJunction();
const tileData = [...base, ...witness.tiles.values()];
const alignment = createFortCanningMergeAlignment(profile);
const roads = fortCanningTrafficRoads(profile, alignment, tileData);
const graph = buildTrafficGraph(tileData, roads);

function stationAt(edge, { x, z }) {
  let best = { distance: Infinity, station: 0 };
  for (let i = 1; i < edge.points.length; i++) {
    const [ax, az] = edge.points[i - 1], [bx, bz] = edge.points[i];
    const dx = bx - ax, dz = bz - az;
    const fraction = Math.max(0, Math.min(1, ((x - ax) * dx + (z - az) * dz) / (dx ** 2 + dz ** 2)));
    const distance = Math.hypot(ax + dx * fraction - x, az + dz * fraction - z);
    if (distance < best.distance) {
      best = { distance, station: edge.cumulative[i - 1] + fraction * Math.hypot(dx, dz) };
    }
  }
  return best;
}

test("only the authored Link and Penang feeder replace their mapped graph edges", () => {
  const plain = buildTrafficGraph(tileData);
  assert.equal(plain.edges.has("159677768:0"), false);
  assert.deepEqual([...roads.authoredRoads.keys()], [
    ...profile.simulation.chain.map(({ edgeId }) => edgeId), "654224115:0",
  ]);
  assert.ok([...roads.authoredRoads.keys()].every(id => graph.edges.get(id).complete));
  assert.deepEqual(graph.edges.get("430502717:0"), plain.edges.get("430502717:0"));
  assert.equal(graph.nodes.get(profile.simulation.exitNodeId).laneDisjointMerge, true);

  const chain = profile.simulation.chain.map(({ edgeId }) => graph.edges.get(edgeId));
  for (let i = 1; i < chain.length; i++) {
    const end = sampleEdge(chain[i - 1], chain[i - 1].length), start = sampleEdge(chain[i], 0);
    const pose = ({ x, y, z }) => [x, y, z];
    assert.deepEqual(pose(end), pose(start));
  }
  assert.equal(heightOnEdge(chain[0], 0), 0);
  assert.equal(heightOnEdge(chain.at(-1), chain.at(-1).length), 0);
});

test("upper traffic and pedestrians cannot stop a Link vehicle over five metres below", () => {
  const crossing = profile.crossings.find(({ edgeId }) => edgeId === "430502717:0");
  const upper = graph.edges.get(crossing.edgeId);
  const lower = graph.edges.get("159677768:0");
  const upperAt = stationAt(upper, crossing.at), lowerAt = stationAt(lower, crossing.at);
  assert.ok(Math.max(upperAt.distance, lowerAt.distance) < .02);
  assert.equal(heightOnEdge(upper, upperAt.station), 0);
  assert.equal(heightOnEdge(lower, lowerAt.station), -5.5);

  const traffic = createTraffic({ graph, maxVehicles: 0 });
  traffic.vehicles.push(
    { id: 1, type: VEHICLE_TYPES[0], edge: lower.id, direction: 1, lane: 1, s: lowerAt.station, speed: 8 },
    { id: 2, type: VEHICLE_TYPES[0], edge: upper.id, direction: 1, lane: 0, s: upperAt.station, speed: 6 },
  );
  const [below, above] = traffic.vehicles.map(traffic.pose);
  assert.ok(Math.hypot(below.x - above.x, below.z - above.z) < .02);
  assert.equal(above.y - below.y, 5.5);
  for (let step = 0; step < 30; step++) traffic.update(1 / 60, below);
  assert.ok(traffic.vehicles[0].s > lowerAt.station + 4);
  assert.ok(traffic.vehicles[1].s > upperAt.station + 2);

  const walkingPoint = sampleEdge(lower, lowerAt.station + 8);
  function besideWalker(y) {
    const traffic = createTraffic({ graph, maxVehicles: 0 });
    const vehicle = { id: 1, type: VEHICLE_TYPES[0], edge: lower.id, direction: 1, lane: 1, s: lowerAt.station, speed: 5 };
    traffic.vehicles.push(vehicle);
    for (let step = 0; step < 180; step++) traffic.update(1 / 60, below, [{ ...walkingPoint, y }]);
    return vehicle.s - lowerAt.station;
  }
  assert.ok(besideWalker(0) > 20, "a pedestrian upstairs leaves the tunnel lane free");
  assert.ok(besideWalker(-5.5) < 5, "the same position on the road still blocks traffic");
});

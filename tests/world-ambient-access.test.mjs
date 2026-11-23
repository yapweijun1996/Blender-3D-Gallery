import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import { pedestrianPaths } from "../src/world/paths.js";
import { signalApproaches } from "../src/world/signals.js";
import { buildTile } from "../src/world/tile-mesh.js";
import { buildTrafficGraph, createTraffic, sampleEdge, VEHICLE_TYPES } from "../src/world/traffic.js";

const near = { x: 0, z: 0 };
const tile = (roads, layers = {}) => ({ x: 0, z: 0, roads, ...layers });
const road = (id, from, to, geometry, properties = {}) => ({
  id, from, to, geometry, class: "primary", oneway: true, lanes: 1, width: 6.8, ...properties,
});
const loadTile = key => JSON.parse(readFileSync(new URL(`../models/world/tiles/${key}.json`, import.meta.url)));

function approaching(traffic, edge, direction = 1, back = .05) {
  const vehicle = { id: traffic.vehicles.length + 1, type: VEHICLE_TYPES[0], edge: edge.id, direction,
    s: edge.length - back, lane: 0, speed: 10, wait: 0 };
  traffic.vehicles.push(vehicle);
  return vehicle;
}

test("ambient spawning honors effective motorcar access", () => {
  for (const access of [undefined, null, "yes", "designated", "permissive", "private", "destination", "permit",
    "customers", "restricted", "no", "unrecognized-access"]) {
    const graph = buildTrafficGraph([tile([road("main", 1, 2, [[0, 0], [200, 0]], { access })])]);
    const traffic = createTraffic({ graph, random: () => .5 });
    const expected = [undefined, null, "yes", "designated", "permissive"].includes(access) ? "main" : null;
    assert.equal(traffic.spawn(near)?.edge ?? null, expected, String(access));
    assert.ok(graph.edges.has("main"), "the shared road graph retains the mapped edge");
  }
});

test("a mapped private road outside the tunnel cohort remains visible without spawning an ambient vehicle", () => {
  const id = "385202254:0"; // Empress Place, across two tiles
  const tiles = ["-5_-3", "-5_-2"].map(key => {
    const map = loadTile(key);
    return { ...map, roads: map.roads.filter(road => road.id === id) };
  });
  assert.ok(tiles.every(({ roads }) => roads.length === 1 && roads[0].access === "private" && !roads[0].tunnel));
  const graph = buildTrafficGraph(tiles);
  const edge = graph.edges.get(id);
  assert.ok(edge.length > 25);
  const at = sampleEdge(edge, edge.length / 2);
  const traffic = createTraffic({ graph, random: () => .5 });
  assert.equal(traffic.spawn({ x: at.x + 120, z: at.z }), null);
});

test("ambient traffic continues along Jalan Beruang instead of reversing into a mapped destination driveway", () => {
  const approach = "1339966865:0", exit = "766061594:0", driveway = "639995078:0";
  const map = loadTile("-45_-90");
  const roads = [driveway, approach, exit].map(id => map.roads.find(road => road.id === id));
  assert.equal(roads[0].access, "destination");
  assert.equal(roads[0].oneway, false);
  assert.equal(roads[0].to, roads[1].to);
  assert.equal(roads[1].to, roads[2].from);
  const graph = buildTrafficGraph([{ ...map, junctions: [], roads }]);
  const traffic = createTraffic({ graph, maxVehicles: 0, random: () => .99 });
  const vehicle = approaching(traffic, graph.edges.get(approach));
  const at = traffic.pose(vehicle);
  traffic.update(.1, at);
  assert.equal(vehicle.edge, exit);
});

test("eligible two-way and service roads remain available for ambient turns in their mapped directions", () => {
  const approach = road("approach", 1, 2, [[0, 0], [0, 90]], { oneway: false });
  const restricted = road("private", 2, 4, [[0, 90], [70, 90]], { access: "private" });
  const service = road("service", 3, 2, [[0, 170], [0, 90]], { class: "service", oneway: false });
  const back = road("back", 1, 5, [[0, 0], [70, 0]], { access: "permissive" });
  const graph = buildTrafficGraph([tile([approach, restricted, service, back])]);
  for (const [direction, expected, nextDirection] of [[1, "service", -1], [-1, "back", 1]]) {
    const traffic = createTraffic({ graph, maxVehicles: 0, random: () => 0 });
    const vehicle = approaching(traffic, graph.edges.get("approach"), direction);
    traffic.update(.1, near);
    assert.equal(vehicle.edge, expected);
    assert.equal(vehicle.direction, nextDirection);
  }
});

test("a stale planned turn and a vehicle on the changed edge cannot survive an access change", () => {
  const approach = road("approach", 1, 2, [[0, 0], [0, 90]]);
  const changed = road("changed", 2, 3, [[0, 90], [80, 90]]);
  const exit = road("exit", 2, 4, [[0, 90], [0, 170]]);
  const graph = buildTrafficGraph([tile([approach, changed, exit])]);
  const traffic = createTraffic({ graph, maxVehicles: 0, random: () => 0 });
  const chooser = approaching(traffic, graph.edges.get("approach"), 1, 5);
  traffic.update(.1, near);
  assert.equal(chooser.next.id, "changed", "the initially allowed turn is cached during lookahead");
  const occupant = approaching(traffic, graph.edges.get("changed"), 1, 40);
  traffic.setGraph(buildTrafficGraph([tile([approach, { ...changed, access: "permit" }, exit])]));
  for (let step = 0; step < 20 && chooser.edge === "approach"; step++) traffic.update(.1, near);
  assert.equal(chooser.edge, "exit");
  assert.ok(!traffic.vehicles.includes(occupant));
});

test("a configured connector stays closed when its authored target is restricted in the source tile", () => {
  const input = road("input", 1, 2, [[0, 0], [100, 0]]);
  const target = road("target", 2, 3, [[100, 0], [200, 0]]);
  const exit = road("exit", 2, 4, [[100, 0], [100, 90]]);
  const sections = target.geometry.map(([x, z]) => ({ x, y: 0, z, rx: 0, rz: 1 }));
  const config = {
    forwardConnectors: new Map([["input", { id: "target", lanes: [0] }]]),
    authoredRoads: new Map([["target", { road: target, sections }]]),
  };
  const traffic = createTraffic({ graph: buildTrafficGraph([tile([input, target, exit])], config), maxVehicles: 0 });
  const openGraph = buildTrafficGraph([tile([input, target, exit])], config);
  const vehicle = approaching(traffic, openGraph.edges.get("input"), 1, 18);
  const closedGraph = buildTrafficGraph([tile([input, { ...target, access: "private" }, exit])], config);
  assert.equal(closedGraph.edges.get("target").sections, sections, "the authored geometry remains for shared consumers");
  traffic.setGraph(closedGraph);
  for (let step = 0; step < 150; step++) traffic.update(.1, near);
  assert.ok(traffic.vehicles.includes(vehicle));
  assert.equal(vehicle.edge, "input");
  assert.equal(vehicle.speed, 0);
  assert.ok(vehicle.s < openGraph.edges.get("input").length);
});

test("a restricted branch does not block a reviewed short stitch or become its continuation", () => {
  const stitch = road("stitch", 1, 2, [[0, 0], [2, 0]], { retainShortTraffic: true });
  const other = road("other", 2, 4, [[2, 0], [2, 100]], { access: "customers" });
  const exit = road("exit", 2, 3, [[2, 0], [102, 0]]);
  for (const [roads, expected] of [[[stitch, other, exit], "exit"], [[stitch, other], null]]) {
    const graph = buildTrafficGraph([tile(roads)]);
    const traffic = createTraffic({ graph, maxVehicles: 0 });
    const vehicle = approaching(traffic, graph.edges.get("stitch"));
    traffic.update(.1, near);
    assert.equal(traffic.vehicles[0]?.edge ?? null, expected);
    if (expected) assert.equal(vehicle.direction, 1);
  }
});

test("access restrictions survive stitching even when another tile fragment is unrestricted", () => {
  const first = road("seam", 1, 2, [[100, 0], [250, 0]]);
  const last = road("seam", 1, 2, [[0, 0], [70, 0]], { access: "destination" });
  const tiles = [tile([first]), tile([last], { x: 1 })];
  for (const ordered of [tiles, tiles.toReversed()]) {
    const graph = buildTrafficGraph(ordered);
    assert.equal(graph.edges.get("seam").length, 220);
    const traffic = createTraffic({ graph, random: () => .5 });
    assert.equal(traffic.spawn({ x: 90, z: 0 }), null);
  }
});

test("access does not remove player asphalt, the mapped crossing, pedestrian paths or signal placement", () => {
  const geometry = [[0, 20], [100, 20]];
  const layers = {
    crossings: [{ point: [60, 20], roadId: "main" }],
    junctions: [{ nodeId: 2, signalised: true }],
    pedestrian: [{ id: "walk", class: "footway", geometry: [[60, 5], [60, 35]] }],
  };
  const open = tile([road("main", 1, 2, geometry)], layers);
  const closed = tile([road("main", 1, 2, geometry, { access: "private" })], layers);
  const openMesh = buildTile(open).ground;
  const closedMesh = buildTile(closed).ground;
  try {
    assert.ok(openMesh.attributes.position.count > 6, "the tile has road and crossing triangles");
    assert.deepEqual(closedMesh.attributes.position.array, openMesh.attributes.position.array);
    assert.deepEqual(closedMesh.attributes.color.array, openMesh.attributes.color.array);
  } finally {
    openMesh.dispose();
    closedMesh.dispose();
  }
  assert.deepEqual(pedestrianPaths([closed]), pedestrianPaths([open]));
  const graph = buildTrafficGraph([closed]);
  assert.deepEqual(graph.nodes.get(2).backward, ["main"], "mission distance generation retains the mapped road link");
  const approaches = signalApproaches(graph);
  assert.equal(approaches.length, 1);
  assert.deepEqual(approaches, signalApproaches(buildTrafficGraph([open])));
});

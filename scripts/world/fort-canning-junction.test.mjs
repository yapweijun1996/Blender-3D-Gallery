import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

import { readFortCanningJunction, isFortCanningJunctionEdgeReady } from "./fort-canning-junction.mjs";
import profile from "./fort-canning-integration.json" with { type: "json" };
import { polylineLength } from "./tile-geometry.mjs";
import { buildTrafficGraph, createTraffic, VEHICLE_TYPES } from "../../src/world/traffic.js";
import { signalApproaches } from "../../src/world/signals.js";
import { createFortCanningMergeAlignment } from "../../src/world/tunnel-integration/merge-alignment.js";

const witness = await readFortCanningJunction();
const graph = buildTrafficGraph([...witness.tiles.values()]);
const TERMINAL = 408999681;

test("the two Penang Road signals keep their complete approach lines and the existing exit anchor", () => {
  const { signalApproaches, tiles } = witness;
  assert.deepEqual(signalApproaches.map(({ signal, wayId }) => [signal, wayId]), [
    [6176417027, 74559749],
    [TERMINAL, 888048851],
    [TERMINAL, 474300998],
    [TERMINAL, 666009287],
  ]);
  const [middle, terminal] = signalApproaches;
  assert.ok(Math.abs(polylineLength(middle.points) - 39.14198219645) < 1e-6);
  assert.ok(Math.abs(polylineLength(terminal.points) - 47.24823988713) < 1e-6);
  assert.deepEqual(terminal.points.at(-1).map(value => Math.round(value * 1e6) / 1e6),
    profile.simulation.exitWitness.edges.at(-1).points.at(-1));
  assert.ok(terminal.points.length > 2 && graph.edges.get("888048851:2").length < 6,
    "the signal approach continues upstream of the crossing's short graph edge");
  assert.deepEqual(tiles.get("-7_-7.json").junctions.find(({ nodeId }) => nodeId === 6176417027).point, [36.97, 110.59]);
  const western = tiles.get("-8_-7.json");
  const marker = western.junctions.find(({ nodeId }) => nodeId === TERMINAL);
  assert.equal(marker.signalised, true);
  assert.deepEqual(marker.point, [194.29, 83.09]);
  assert.deepEqual(western.crossings.find(({ id }) => id === 7888967675).point, [199.98, 84.74]);
  assert.equal(witness.fixture.elements.find(({ type, id }) => type === "node" && id === 7888967675).tags["crossing:signals"], "yes");
});

test("the terminal admits the three signed approaches to one public exit", () => {
  const { movements, restrictions, ways } = witness;
  assert.deepEqual(movements.filter(({ via }) => via === TERMINAL), [
    { via: TERMINAL, from: 888048851, to: 75551640, turn: "through", fromLanes: [0, 1, 2, 3, 4] },
    { via: TERMINAL, from: 474300998, to: 75551640, turn: "right", fromLanes: [0, 1, 2] },
    { via: TERMINAL, from: 666009287, to: 75551640, turn: "left", fromLanes: [0, 1] },
  ]);
  assert.equal(ways.get(774912613).tags.access, "private");
  assert.ok(![...witness.tiles.values()].some(tile => tile.roads.some(road => road.wayId === 774912613)));
  assert.deepEqual(restrictions.map(({ id, tags, members }) => [id, tags.restriction, members]), [
    [12351517, "no_u_turn", [
      { type: "way", ref: 666009287, role: "from" },
      { type: "node", ref: TERMINAL, role: "via" },
      { type: "way", ref: 774912613, role: "to" },
    ]],
  ]);
  assert.deepEqual(graph.nodes.get(TERMINAL).forward, ["75551640:0"]);
  assert.deepEqual(graph.nodes.get(TERMINAL).backward.toSorted(), ["474300998:5", "666009287:1", "888048851:2"]);
  assert.ok([...graph.edges.values()].every(({ oneway, layer }) => oneway && layer === 0));
});

test("the first public fork carries the tagged left and through choices and leaves the right unresolved", () => {
  const { movements, unresolvedForkLanes } = witness;
  assert.deepEqual(movements.filter(({ via }) => via !== TERMINAL), [
    { via: 6097184849, from: 75551640, to: 649770884, turn: "through", fromLanes: [0, 1, 2, 3, 4] },
    { via: 1275666711, from: 649770884, to: 112154347, turn: "left", fromLanes: [0, 1] },
    { via: 1275666711, from: 649770884, to: 173767817, turn: "through", fromLanes: [1, 2, 3, 4] },
  ]);
  assert.deepEqual(unresolvedForkLanes, [{ lane: 4, turn: "right" }, { lane: 5, turn: "right" }]);
  assert.deepEqual(graph.nodes.get(1275666711).forward.toSorted(), ["112154347:0", "173767817:0"]);
  assert.deepEqual([graph.edges.get("75551640:0").lanes, graph.edges.get("649770884:0").lanes], [5, 6]);
  assert.ok(Math.abs(graph.edges.get("75551640:0").length - 19.44) < .02);
  assert.ok(Math.abs(graph.edges.get("649770884:0").length - 18.03) < .02);
});

test("only three existing tiles receive the public-road overlay and their unrelated map features fit", () => {
  assert.deepEqual([...witness.tiles.keys()], ["-8_-8.json", "-8_-7.json", "-7_-7.json"]);
  const appliedTiles = new Map();
  for (const [file, overlay] of witness.tiles) {
    const current = JSON.parse(readFileSync(new URL("../../models/world/tiles/" + file, import.meta.url)));
    assert.deepEqual([overlay.x, overlay.z], [current.x, current.z]);
    const applied = { ...current };
    for (const layer of ["roads", "kerbs", "junctions", "crossings"]) applied[layer] = [...current[layer], ...overlay[layer]];
    assert.ok(Buffer.byteLength(JSON.stringify(applied)) < 120_000);
    appliedTiles.set(file, applied);
  }
  const western = appliedTiles.get("-8_-7.json");
  assert.ok(western.buildings.some(({ id }) => id === 46522845));
  assert.ok(western.parks.some(({ id }) => id === 52235738));
  assert.ok(western.pedestrian.some(({ id }) => id === "194775119:0"));
  assert.ok(appliedTiles.get("-7_-7.json").roads.some(({ id }) => id === "39351292:0"));
  assert.ok(isFortCanningJunctionEdgeReady(witness, "74559749:1", appliedTiles));
  assert.ok(isFortCanningJunctionEdgeReady(witness, "474300998:0", appliedTiles));
});

test("each crossed boundary joins the exact road fragment and either missing shard keeps that route unavailable", () => {
  const seams = [
    { id: "74559749:1", from: "-7_-7.json", to: "-8_-7.json", point: [-1750, -1650.85] },
    { id: "474300998:0", from: "-8_-8.json", to: "-8_-7.json", point: [-1775.09, -1750] },
  ];
  for (const { id, from, to, point } of seams) {
    const at = (file, end) => {
      const tile = witness.tiles.get(file);
      const [x, z] = tile.roads.find(road => road.id === id).geometry.at(end);
      return [250 * tile.x + x, 250 * tile.z + z];
    };
    assert.deepEqual(at(from, -1), point);
    assert.deepEqual(at(to, 0), point);
    assert.ok(isFortCanningJunctionEdgeReady(witness, id, witness.tiles));
    for (const missing of [from, to]) {
      const loaded = new Map(witness.tiles);
      loaded.delete(missing);
      assert.equal(isFortCanningJunctionEdgeReady(witness, id, loaded), false);
    }
    const altered = structuredClone(witness.tiles);
    const road = altered.get(to).roads.find(candidate => candidate.id === id);
    road.geometry[0][0] += .01;
    assert.equal(isFortCanningJunctionEdgeReady(witness, id, altered), false);
  }
});

test("all five AI lanes join the real Penang continuation from the authored merge", () => {
  const alignment = createFortCanningMergeAlignment(profile);
  const current = JSON.parse(readFileSync(new URL("../../models/world/tiles/-7_-7.json", import.meta.url)));
  const downstream = "888048852:0";
  const terminal = profile.simulation.chain.at(-1);
  const feeds = [
    { id: terminal.edgeId, path: alignment.link.filter(({ s }) => s >= terminal.start), lanes: [0, 1, 2] },
    { id: "654224115:0", path: alignment.penang, lanes: [3, 4] },
  ];
  const roads = feeds.map(({ id, path }) => ({
    ...current.roads.find(road => road.id === id),
    geometry: path.map(({ x, z }) => [x, z]),
  }));
  const forwardConnectors = new Map(feeds.map(({ id, lanes }) => [id, { id: downstream, lanes }]));
  const graph = buildTrafficGraph([...witness.tiles.values(), { x: 0, z: 0, roads }], { forwardConnectors });
  assert.equal(graph.nodes.get(profile.simulation.exitNodeId).laneDisjointMerge, true);
  const traffic = createTraffic({ graph, maxVehicles: 0 });
  let id = 0;
  for (const feed of feeds) {
    for (let lane = 0; lane < feed.lanes.length; lane++) {
      traffic.vehicles.push({
        id: id++, type: VEHICLE_TYPES[0], edge: feed.id, direction: 1,
        lane, s: graph.edges.get(feed.id).length - 2, speed: 7,
      });
    }
  }
  for (let step = 0; step < 30; step++) traffic.update(1 / 60, alignment.seam);
  assert.deepEqual(traffic.vehicles.map(({ edge, lane }) => [edge, lane]),
    [0, 1, 2, 3, 4].map(lane => [downstream, lane]));
});

test("the real terminal signal brakes a bus before its mapped crossing and releases it on green", () => {
  const upstream = "888048851:0", terminal = "888048851:2";
  const stopOffset = 15;
  const graph = buildTrafficGraph([...witness.tiles.values()], {
    signalApproachChains: [{ edges: [upstream, terminal], stopOffset }],
  });
  const preceding = graph.edges.get(upstream), final = graph.edges.get(terminal);
  assert.equal(preceding.forwardSignal.approach, final.forwardSignal.approach);
  const line = preceding.length + final.length - stopOffset;
  const bus = VEHICLE_TYPES.find(({ id }) => id === "bus");
  const zebraHalfLength = 1.5;
  assert.ok(preceding.length - line - bus.length / 2 - zebraHalfLength > 1, "the bus clears the painted crossing");

  const approaches = signalApproaches(graph);
  assert.equal(approaches.filter(({ signalBearing }) => signalBearing).length, 1);
  assert.equal(approaches.length, signalApproaches(buildTrafficGraph([...witness.tiles.values()])).length + 1);

  const traffic = createTraffic({ graph, maxVehicles: 0 });
  const near = { x: preceding.points.at(-1)[0], z: preceding.points.at(-1)[1] };
  traffic.update(29, near);
  const vehicle = { id: 1, type: bus, edge: upstream, direction: 1, lane: 0, s: line - 24, speed: 11 };
  traffic.vehicles.push(vehicle);
  for (let step = 0; step < 360; step++) traffic.update(1 / 60, near);
  assert.equal(vehicle.edge, upstream, "the red signal is obeyed before the short crossing edge");
  assert.ok(vehicle.s <= line + .05 && vehicle.s >= line - .5);
  assert.ok(vehicle.speed < .2);

  const outbound = "75551640:0";
  for (let step = 0; step < 2000 && vehicle.edge !== outbound; step++) traffic.update(1 / 60, near);
  assert.equal(vehicle.edge, outbound);
  assert.ok(traffic.time >= 58, "the vehicle crosses on the next green");
});

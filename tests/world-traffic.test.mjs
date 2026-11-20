import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";
import { buildTrafficGraph, createRandom, createTraffic, phaseOf, sampleEdge, signalState } from "../src/world/traffic.js";

const tilesDir = "models/world/tiles/";
const loadTiles = (radius = 2, cx = 0, cz = 0) => {
  const tiles = [];
  for (let dz = -radius; dz <= radius; dz++) for (let dx = -radius; dx <= radius; dx++) {
    const file = `${tilesDir}${cx + dx}_${cz + dz}.json`;
    if (fs.existsSync(file)) tiles.push(JSON.parse(fs.readFileSync(file, "utf8")));
  }
  return tiles;
};

test("the traffic graph stitches road edges from the map tiles", () => {
  const graph = buildTrafficGraph(loadTiles());
  assert.ok(graph.edges.size > 100, `${graph.edges.size} edges`);
  assert.ok(graph.signalised.size > 3, `${graph.signalised.size} signalised junctions`);
  for (const edge of graph.edges.values()) {
    assert.ok(edge.length >= 4 && edge.points.length >= 2);
    assert.equal(edge.cumulative.length, edge.points.length);
  }
  const connected = [...graph.nodes.values()].filter(node => node.forward.length + node.backward.length >= 2).length;
  assert.ok(connected > 50, `${connected} junction nodes join two or more edges`);
});

test("signals alternate: while one phase is green the other is red", () => {
  for (let t = 0; t < 120; t += 0.5) {
    const a = signalState(0, t), b = signalState(1, t);
    assert.ok(!(a === "green" && b !== "red"), `t=${t}`);
    assert.ok(!(b === "green" && a !== "red"), `t=${t}`);
  }
  assert.equal(phaseOf(1, 0.1), 0);
  assert.equal(phaseOf(0.1, 1), 1);
});

test("simulated traffic stays on the roads, keeps a gap and keeps moving", () => {
  const graph = buildTrafficGraph(loadTiles());
  const near = { x: 0, z: 0 };
  const traffic = createTraffic({ graph, random: createRandom(7), maxVehicles: 30 });
  let moving = 0, samples = 0, overlaps = 0;
  for (let step = 0; step < 60 * 90; step++) {
    traffic.update(1 / 60, near);
    if (step % 60 === 0) {
      for (const vehicle of traffic.vehicles) {
        const edge = graph.edges.get(vehicle.edge);
        assert.ok(edge, "vehicle is on a known edge");
        assert.ok(vehicle.s >= 0 && vehicle.s <= edge.length + 0.01, `s ${vehicle.s} of ${edge.length}`);
        const pose = traffic.pose(vehicle);
        assert.ok(Number.isFinite(pose.x) && Number.isFinite(pose.z));
        const at = sampleEdge(edge, vehicle.s, vehicle.direction);
        assert.ok(Math.hypot(pose.x - at.x, pose.z - at.z) <= edge.width / 2 + 2, "lane offset stays within the carriageway");
        samples++; if (vehicle.speed > 1) moving++;
        for (const other of traffic.vehicles) {
          if (other.id >= vehicle.id || other.edge !== vehicle.edge || other.direction !== vehicle.direction || other.lane !== vehicle.lane) continue;
          if (Math.abs(other.s - vehicle.s) < (other.type.length + vehicle.type.length) / 2 - 1) overlaps++;
        }
      }
    }
  }
  assert.ok(traffic.vehicles.length >= 20, `${traffic.vehicles.length} vehicles`);
  assert.ok(moving / samples > 0.4, `${Math.round(100 * moving / samples)}% of samples were moving`);
  assert.ok(overlaps / samples < 0.02, `${overlaps} overlapping samples of ${samples}`);
});

test("a vehicle stops at a red signal and drives on at green", () => {
  const edge = { id: "a:0", from: 1, to: 2, oneway: true, lanes: 1, speed: 13.9, points: [[0, 0], [0, 200]], cumulative: [0, 200], length: 200, width: 3.4, class: "primary" };
  const graph = { edges: new Map([[edge.id, edge]]), nodes: new Map([[1, { id: 1, forward: [edge.id], backward: [], signalised: false }], [2, { id: 2, forward: [], backward: [edge.id], signalised: true }]]), signalised: new Set([2]) };
  const traffic = createTraffic({ graph, random: createRandom(1), maxVehicles: 0 });
  // Phase 1 (north-south approach) is red for the first seconds of the second half cycle: start the clock there.
  const redStart = 2 * (24 + 3 + 2) / 2; // phase 1 turns red when phase 0's half cycle begins... find a time when it is red
  let time = 0; while (signalState(1, time) !== "red") time += 0.5;
  traffic.update(time, { x: 0, z: 100 }); // advance the clock (no vehicles yet)
  void redStart;
  const vehicle = { id: 1, type: { length: 4.4 }, edge: edge.id, direction: 1, s: 60, lane: 0, speed: 12, wait: 0 };
  traffic.vehicles.push(vehicle);
  let stoppedAt = null;
  for (let step = 0; step < 60 * 14; step++) {
    traffic.update(1 / 60, { x: 0, z: 100 });
    if (signalState(1, traffic.time) !== "red") break;
    if (vehicle.speed < 0.05 && stoppedAt === null) stoppedAt = vehicle.s;
  }
  assert.ok(stoppedAt !== null, "the vehicle came to a stop");
  assert.ok(stoppedAt < 197 && stoppedAt > 150, `stopped at ${stoppedAt}, before the line at 196`);
  for (let step = 0; step < 60 * 40 && vehicle.edge === edge.id; step++) traffic.update(1 / 60, { x: 0, z: 100 });
  assert.ok(vehicle.edge !== edge.id || traffic.vehicles.indexOf(vehicle) < 0 || vehicle.s > 196, "it drove on after the light turned green");
});

test("a vehicle stops for a pedestrian standing in its lane and moves on when they leave", () => {
  const edge = { id: "b:0", from: 1, to: 2, oneway: true, lanes: 1, speed: 13.9, points: [[0, 0], [0, 300]], cumulative: [0, 300], length: 300, width: 3.4, class: "primary" };
  const graph = { edges: new Map([[edge.id, edge]]), nodes: new Map([[1, { id: 1, forward: [edge.id], backward: [], signalised: false }], [2, { id: 2, forward: [], backward: [edge.id], signalised: false }]]), signalised: new Set() };
  const traffic = createTraffic({ graph, random: createRandom(3), maxVehicles: 0 });
  const vehicle = { id: 1, type: { length: 4.4, width: 1.8 }, edge: edge.id, direction: 1, s: 20, lane: 0, speed: 12, wait: 0 };
  traffic.vehicles.push(vehicle);
  const near = { x: 0, z: 100 };
  // The lane offset of a single lane is half a lane to the left of the centre line: x = +1.7 (left of +Z travel is +X).
  const pedestrian = { x: 1.7, z: 120 };
  for (let step = 0; step < 60 * 20; step++) traffic.update(1 / 60, near, [pedestrian]);
  assert.ok(vehicle.speed < 0.05, `speed ${vehicle.speed}`);
  assert.ok(vehicle.s < 120, `stopped at ${vehicle.s}, before the pedestrian at 120`);
  assert.ok(vehicle.s > 90, `stopped close to the pedestrian (${vehicle.s})`);
  for (let step = 0; step < 60 * 10; step++) traffic.update(1 / 60, near, []);
  assert.ok(vehicle.s > 130 || traffic.vehicles.indexOf(vehicle) < 0, "drove on after the pedestrian left");
});

test("at an unsignalised junction vehicles from two roads take turns and never share the junction", () => {
  // Two roads meeting at node 3 and one exit road: a T-junction.
  const make = (id, from, to, points) => {
    const cumulative = [0]; for (let i = 1; i < points.length; i++) cumulative.push(cumulative[i - 1] + Math.hypot(points[i][0] - points[i - 1][0], points[i][1] - points[i - 1][1]));
    return { id, from, to, oneway: true, lanes: 1, speed: 13.9, points, cumulative, length: cumulative.at(-1), width: 3.4, class: "secondary" };
  };
  const a = make("a:0", 1, 3, [[-120, 0], [0, 0]]), b = make("b:0", 2, 3, [[0, -120], [0, 0]]), exit = make("x:0", 3, 4, [[0, 0], [160, 0]]);
  const nodes = new Map([[1, { id: 1, forward: [a.id], backward: [], signalised: false }], [2, { id: 2, forward: [b.id], backward: [], signalised: false }],
    [3, { id: 3, forward: [exit.id], backward: [a.id, b.id], signalised: false }], [4, { id: 4, forward: [], backward: [exit.id], signalised: false }]]);
  const graph = { edges: new Map([a, b, exit].map(edge => [edge.id, edge])), nodes, signalised: new Set() };
  const traffic = createTraffic({ graph, random: createRandom(5), maxVehicles: 0 });
  const car = (id, edge, s) => ({ id, type: { length: 4.4, width: 1.8 }, edge: edge.id, direction: 1, s, lane: 0, speed: 12, wait: 0 });
  const first = car(1, a, 60), second = car(2, b, 62);
  traffic.vehicles.push(first, second);
  const near = { x: 0, z: 0 };
  let sharedSteps = 0, passed = 0;
  for (let step = 0; step < 60 * 40; step++) {
    traffic.update(1 / 60, near);
    const inside = traffic.vehicles.filter(vehicle => { const edge = graph.edges.get(vehicle.edge); const d = vehicle.edge === "x:0" ? vehicle.s : edge.length - vehicle.s; return Math.abs(d) < 3; });
    if (inside.length > 1) sharedSteps++;
  }
  for (const vehicle of [first, second]) if (vehicle.edge === "x:0" || traffic.vehicles.indexOf(vehicle) < 0) passed++;
  assert.equal(passed, 2, "both vehicles got through");
  assert.equal(sharedSteps, 0, `${sharedSteps} steps with two vehicles in the junction`);
});

test("with give-way and signals the traffic does not gridlock over five minutes", () => {
  const graph = buildTrafficGraph(loadTiles());
  for (const seed of [2, 5]) {
    const traffic = createTraffic({ graph, random: createRandom(seed), maxVehicles: 34 });
    let samples = 0, stuck = 0;
    for (let step = 0; step < 60 * 300; step++) {
      traffic.update(1 / 60, { x: 0, z: 0 });
      if (step % 120) continue;
      for (const vehicle of traffic.vehicles) { samples++; if (vehicle.wait > 30) stuck++; }
    }
    assert.ok(stuck / samples < 0.03, `seed ${seed}: ${stuck} of ${samples} samples stuck for over 30 s`);
  }
});

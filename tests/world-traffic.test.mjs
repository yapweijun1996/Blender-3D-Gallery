import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";
import { signalApproaches } from "../src/world/signals.js";
import { buildTrafficGraph, createRandom, createTraffic, phaseOf, sampleEdge, signalState, VEHICLE_TYPES } from "../src/world/traffic.js";

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

const crossingX = 135;
const crossingZ = 90;
const tailLength = 5.9;
const stopOffset = 15;
const crossingChain = { edges: ["upstream", "approach", "tail"], stopOffset };

function crossingSignalGraph(signalApproachChains, { terminal = true, turn = false } = {}) {
  const road = (id, from, to, geometry) => ({ id, from, to, oneway: true, lanes: 1, geometry, class: "primary", maxspeed: 50 });
  const roads = [
    road("upstream", 1, 2, [[10, crossingZ], [55, crossingZ]]),
    road("approach", 2, 3, [[55, crossingZ], [crossingX, crossingZ]]),
    road("tail", 3, 4, [[crossingX, crossingZ], [crossingX, crossingZ + tailLength]]),
    road("onward", 4, 5, [[crossingX, crossingZ + tailLength], [crossingX, 180]]),
    road("other", 6, 7, [[160, 60], [220, 60]]),
  ];
  if (turn) roads.push(road("turn", 3, 8, [[crossingX, crossingZ], [180, crossingZ]]));
  const junctions = [2, ...(terminal ? [4] : []), 7].map(nodeId => ({ nodeId, signalised: true }));
  return buildTrafficGraph([{ x: 0, z: 0, roads, junctions }], { signalApproachChains });
}

test("a signal beyond a short crossing split stops long vehicles upstream and releases them on green", () => {
  const graph = crossingSignalGraph([crossingChain, crossingChain]);
  const poles = signalApproaches(graph);
  const normalPoles = signalApproaches(crossingSignalGraph());
  assert.equal(normalPoles.length, 2, "the unrelated signal and the earlier signal have ordinary poles");
  assert.equal(poles.length, normalPoles.length + 1, "the configured terminal gets a single pole");
  assert.deepEqual(poles.filter(pole => !pole.signalBearing), normalPoles);
  const pole = poles.find(item => item.signalBearing);
  const expectedLine = crossingX - (stopOffset - tailLength);
  assert.ok(Math.abs(pole.x - expectedLine) < 1e-6);
  assert.ok(pole.z < crossingZ, "the pole sits on the local left verge");
  assert.equal(phaseOf(pole.dx, pole.dz), 0);
  assert.equal(pole.phase, 1, "the phase follows the terminal segment after the turn");

  const traffic = createTraffic({ graph, maxVehicles: 0 });
  const near = { x: crossingX, z: crossingZ };
  const longest = VEHICLE_TYPES.reduce((long, type) => type.length > long.length ? type : long);
  const vehicle = { id: 1, type: longest, edge: "approach", direction: 1, s: 48, lane: 0, speed: 11, wait: 0 };
  traffic.vehicles.push(vehicle);
  let brakedBeforeSplit = false;
  for (let step = 0; step < 8 * 60; step++) {
    traffic.update(1 / 60, near);
    assert.equal(vehicle.edge, "approach", "the red light keeps the vehicle behind the crossing");
    const pose = traffic.pose(vehicle);
    if (vehicle.speed < 10 && pose.x < crossingX - 10) brakedBeforeSplit = true;
    assert.ok(pose.x <= pole.x + 1e-6, "the vehicle center does not pass the shared red stop line");
  }
  assert.ok(brakedBeforeSplit);
  assert.equal(vehicle.speed, 0);
  assert.ok(Math.abs(traffic.pose(vehicle).x - pole.x) < .1, "the center reaches the shared stop line");
  const barsStart = crossingX - 1.5; // zebra bars extend 1.5 m either side of the mapped crossing center
  assert.ok(traffic.pose(vehicle).x + longest.length / 2 < barsStart - 1, "the vehicle nose clears the paint by at least one metre");
  for (let step = 0; step < 30 * 60 && vehicle.edge !== "onward"; step++) traffic.update(1 / 60, near);
  assert.equal(traffic.signalState(pole.signalBearing.dx, pole.signalBearing.dz), "green");
  assert.equal(vehicle.edge, "onward", "the vehicle continued through the terminal junction on green");
});

test("a signal chain needs an adjoining route and a verified terminal with room beyond the earlier signal", () => {
  const ordinary = signalApproaches(crossingSignalGraph());
  for (const chain of [{ edges: ["upstream", "tail"], stopOffset }, { ...crossingChain, stopOffset: 100 }]) {
    assert.deepEqual(signalApproaches(crossingSignalGraph([chain])), ordinary);
  }
  assert.deepEqual(signalApproaches(crossingSignalGraph([crossingChain], { turn: true })), ordinary);
  assert.deepEqual(signalApproaches(crossingSignalGraph([crossingChain], { terminal: false })), ordinary);
});

test("traffic does not spawn beyond a configured red stop line", () => {
  function makeTraffic(graph) {
    const values = [.25, .985]; // select the approach near its downstream end
    let index = 0;
    return createTraffic({ graph, random: () => values[index++ % values.length] });
  }
  const near = { x: crossingX - 90, z: crossingZ };
  const ordinary = makeTraffic(crossingSignalGraph());
  assert.equal(ordinary.spawn(near).edge, "approach");
  const configured = makeTraffic(crossingSignalGraph([crossingChain]));
  assert.equal(configured.spawn(near), null);
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

test("traffic keeps its nose behind a slow player vehicle on the same deck and ignores it on another deck", () => {
  const road = { id: "lower", from: 1, to: 2, oneway: true, lanes: 1, maxspeed: 50, class: "primary" };
  const sections = [0, 300].map(z => ({ x: 0, y: -5.5, z, rx: -1, rz: 0 }));
  const graph = buildTrafficGraph([], { authoredRoads: new Map([[road.id, { road, sections }]]) });
  const near = { x: 0, z: 95 };
  for (const y of [-4.8, 0.7]) {
    const traffic = createTraffic({ graph, maxVehicles: 0 });
    const type = VEHICLE_TYPES[0];
    const follower = { id: 1, type, edge: road.id, s: 60, lane: 0, direction: 1, speed: 12 };
    traffic.vehicles.push(follower);
    const player = { x: 0, y, z: 71, halfLength: 3 };
    for (let step = 0; step < 6 * 60; step++) {
      player.z += 2 / 60;
      traffic.update(1 / 60, near, [player]);
      if (y < 0) assert.ok(player.z - player.halfLength - (follower.s + type.length / 2) >= .99, "the cars keep a bumper gap");
    }
    if (y > 0) assert.ok(follower.s > player.z + 30, "another deck is not a driving obstacle");
    else assert.ok(follower.s > 70, "the follower continues behind the slower player");
  }
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

const mergeConnectors = new Map([
  ["link", { id: "exit", lanes: [0, 1, 2] }],
  ["penang", { id: "exit", lanes: [3, 4] }],
]);
const mergeNear = { x: 120, z: 100 };

function mergeGraph(forwardConnectors = mergeConnectors, { exit = true, otherExit = false } = {}) {
  const road = (id, from, to, lanes, geometry) => ({ id, from, to, lanes, geometry, maxspeed: 40, oneway: true, class: "primary" });
  const roads = [road("link", 1, 3, 3, [[20, 96.6], [120, 96.6]]), road("penang", 2, 3, 2, [[20, 105.1], [120, 105.1]])];
  if (exit) roads.push(road("exit", 3, 4, 5, [[120, 100], [245, 100]]));
  if (otherExit) roads.push(road("other", 3, 5, 2, [[120, 100], [140, 130]]));
  return buildTrafficGraph([{ x: 0, z: 0, roads }], { forwardConnectors });
}

function trafficCar(id, edge, lane, s, speed) {
  return { id, type: { length: 4.4, width: 1.8 }, edge, direction: 1, s, lane, speed, wait: 0 };
}

test("connected 3+2 feeder lanes continue into all five exit lanes side by side", () => {
  const graph = mergeGraph();
  assert.equal(graph.nodes.get(3).laneDisjointMerge, true);
  const traffic = createTraffic({ graph, maxVehicles: 0 });
  const cars = [trafficCar(1, "link", 0, 80, 8), trafficCar(2, "link", 1, 80, 8), trafficCar(3, "link", 2, 80, 8),
    trafficCar(4, "penang", 0, 80, 8), trafficCar(5, "penang", 1, 80, 8)];
  traffic.vehicles.push(...cars);
  const laneCenters = cars.map(car => traffic.pose(car).z);
  const crossed = new Map();
  for (let step = 0; step < 180; step++) {
    traffic.update(1 / 60, mergeNear);
    for (const [index, car] of cars.entries()) {
      const at = traffic.pose(car);
      assert.ok(Math.abs(at.z - laneCenters[index]) < 1e-9, "the lane keeps its lateral position across the seam");
      if (car.edge === "exit" && !crossed.has(car.id)) crossed.set(car.id, step);
    }
  }
  assert.deepEqual(cars.map(({ edge, lane }) => [edge, lane]), [["exit", 0], ["exit", 1], ["exit", 2], ["exit", 3], ["exit", 4]]);
  assert.equal(crossed.size, 5);
  assert.ok(Math.max(...crossed.values()) - Math.min(...crossed.values()) <= 1, "unrelated lanes do not yield to one another");
});

for (const [branch, lane] of [["link", 0], ["penang", 3]]) {
  test(`${branch} traffic follows the leader in its mapped exit lane`, () => {
    const traffic = createTraffic({ graph: mergeGraph(), maxVehicles: 0 });
    const follower = trafficCar(1, branch, 0, 78, 9);
    const leader = trafficCar(2, "exit", lane, 4, 0);
    const clear = trafficCar(3, branch === "link" ? "penang" : "link", 0, 78, 9);
    const at = traffic.pose(leader);
    const obstacle = { x: at.x + 3, z: at.z };
    traffic.vehicles.push(follower, leader, clear);
    for (let i = 0; i < 360; i++) traffic.update(1 / 60, mergeNear, [obstacle]);
    assert.equal(clear.edge, "exit", "traffic in a different lane can continue");
    assert.equal(follower.edge, branch, "the follower waits for the leader before entering the same lane");
    assert.ok(follower.speed < .1);
    assert.ok(traffic.pose(leader).x - traffic.pose(follower).x >= 6.25, "the vehicle keeps a bumper gap across the seam");
    for (let i = 0; i < 240; i++) traffic.update(1 / 60, mergeNear);
    assert.equal(follower.edge, "exit");
    assert.equal(follower.lane, lane);
  });
}

test("a configured lane connection waits while its exit is absent and resumes after graph replacement", () => {
  const traffic = createTraffic({ graph: mergeGraph(), maxVehicles: 0 });
  const car = trafficCar(1, "penang", 1, 83, 9);
  traffic.vehicles.push(car);
  traffic.update(1 / 60, mergeNear);
  traffic.setGraph(mergeGraph(mergeConnectors, { exit: false, otherExit: true }));
  for (let i = 0; i < 240; i++) traffic.update(1 / 60, mergeNear);
  assert.equal(traffic.vehicles[0], car);
  assert.equal(car.edge, "penang", "a loaded alternative is not the configured destination");
  assert.equal(car.speed, 0);
  assert.ok(traffic.pose(car).x <= mergeNear.x - 2);
  traffic.setGraph(mergeGraph());
  for (let i = 0; i < 180; i++) traffic.update(1 / 60, mergeNear);
  assert.equal(car.edge, "exit");
  assert.equal(car.lane, 4);
});

test("incomplete or conflicting lane connections preserve ordinary junction priority", () => {
  const conflict = new Map(mergeConnectors).set("penang", { id: "exit", lanes: [2, 3] });
  const incomplete = new Map([["link", mergeConnectors.get("link")]]);
  const invalid = new Map(mergeConnectors).set("penang", { id: "exit", lanes: [3, 5] });
  const crossing = new Map(mergeConnectors).set("penang", { id: "exit", lanes: [4, 3] });
  for (const graph of [mergeGraph(conflict), mergeGraph(incomplete), mergeGraph(invalid), mergeGraph(crossing),
    mergeGraph(mergeConnectors, { otherExit: true })]) {
    assert.equal(graph.nodes.get(3).laneDisjointMerge, undefined);
  }
  assert.equal(mergeGraph(invalid).edges.get("penang").forwardConnector, null, "an out-of-range map is unavailable");
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

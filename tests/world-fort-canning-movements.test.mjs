import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';
import { buildTrafficGraph, createTraffic, VEHICLE_TYPES } from '../src/world/traffic.js';
import { signalApproaches } from '../src/world/signals.js';
import { prepareFortCanningRoute } from '../src/world/tunnel-integration/route.js';

const prepared = await prepareFortCanningRoute(async key => {
  const file = new URL(`../models/world/tiles/${key}.json`, import.meta.url);
  return JSON.parse(await readFile(file, 'utf8'));
}, new AbortController().signal);
const graph = buildTrafficGraph(prepared.tiles.values(), prepared.trafficOptions);
const sedan = VEHICLE_TYPES.find(({ id }) => id === 'sedan');
const dt = 1 / 60;
const terminal = 408999681;

function car(id, edge, s, lane, speed = 5) {
  return { id, type: sedan, edge, s, direction: 1, lane, speed, wait: 0 };
}

function approachPoint(edge) {
  const [x, z] = edge.points.at(-1);
  return { x, z };
}

test('the Penang fork uses only its mapped per-lane movements and leaves the unresolved right lane closed', () => {
  const last = graph.edges.get('888048851:2');
  const westbound = graph.edges.get('649770884:0');
  const left = '112154347:0', through = '173767817:0';
  assert.equal(graph.edges.has('774912613:0'), false, 'the private drive is drawn separately from traffic');
  assert.deepEqual(last.forwardMovements.map(options => options.map(({ id, lane }) => [id, lane])),
    [0, 1, 2, 3, 4].map(lane => [['75551640:0', lane]]));
  assert.deepEqual(westbound.forwardMovements.map(options => options.map(({ id, lane }) => [id, lane])),
    [[[left, 0]], [[left, 1], [through, 1]], [[through, 2]], [[through, 3]], [[through, 4]], []]);

  for (const { lane, draw, destination } of [
    { lane: 0, draw: .99, destination: left }, { lane: 1, draw: 0, destination: left },
    { lane: 1, draw: .99, destination: through }, { lane: 4, draw: 0, destination: through },
  ]) {
    const traffic = createTraffic({ graph, maxVehicles: 0, random: () => draw });
    const vehicle = car(1, westbound.id, 1, lane);
    traffic.vehicles.push(vehicle);
    for (let i = 0; i < 300 && vehicle.edge === westbound.id; i++) traffic.update(dt, approachPoint(westbound));
    assert.equal(vehicle.edge, destination);
  }

  const traffic = createTraffic({ graph, maxVehicles: 0 });
  const unknown = car(1, westbound.id, 2, 5);
  traffic.vehicles.push(unknown);
  for (let i = 0; i < 600; i++) traffic.update(dt, approachPoint(westbound));
  assert.equal(unknown.edge, westbound.id);
  assert.ok(unknown.speed < .1, 'the unverified right-turn route remains unavailable');
});

test('opposing Penang Lane feeders share a green without sharing the level junction', () => {
  const traffic = createTraffic({ graph, maxVehicles: 0 });
  const north = graph.edges.get('474300998:0'), south = graph.edges.get('666009287:0');
  const near = approachPoint(graph.edges.get('888048851:2'));
  const approaches = signalApproaches(graph).filter(({ signalBearing }) => signalBearing);
  assert.equal(approaches.length, 3, 'all three terminal stop lines have a lamp');
  assert.equal(north.forwardSignal.approach.phase, south.forwardSignal.approach.phase);
  const { dx, dz } = south.forwardSignal.approach.bearing;
  traffic.update(29, near);
  assert.equal(traffic.signalState(dx, dz), 'green');
  const vehicles = [car(1, north.id, north.forwardSignal.toLine - 4, 0), car(2, south.id, south.forwardSignal.toLine - 4, 0)];
  traffic.vehicles.push(...vehicles);
  const finished = new Map(), prior = new Map();
  let waitingOnGreen = false;
  for (let step = 0; step < 24 * 60 && finished.size < 2; step++) {
    traffic.update(dt, near);
    const entering = vehicles.filter(vehicle => vehicle.movement?.via === terminal).length;
    assert.ok(entering <= 1, 'opposing greens do not share the connector zone');
    waitingOnGreen ||= entering === 1 && vehicles.some(vehicle => vehicle.speed < .05);
    for (const vehicle of vehicles) {
      const at = traffic.pose(vehicle), before = prior.get(vehicle.id);
      assert.equal(at.y, 0);
      if (before) assert.ok(Math.hypot(at.x - before.x, at.z - before.z) < .25, 'the turn has a continuous pose');
      prior.set(vehicle.id, at);
      if (vehicle.edge === '75551640:0') finished.set(vehicle.id, vehicle.lane);
    }
  }
  assert.ok(waitingOnGreen);
  assert.deepEqual([...finished.entries()].sort(), [[1, 2], [2, 0]]);
});

test('simultaneously green approaches into the same destination lane wait for the leading vehicle to clear', () => {
  const road = (id, from, to, geometry) => ({ id, from, to, geometry, width: 3.4, lanes: 1, oneway: true, class: 'primary' });
  const roads = [road('north', 1, 3, [[100, 40], [100, 100]]), road('south', 2, 3, [[100, 160], [100, 100]]),
    road('exit', 3, 4, [[100, 100], [10, 100]]), { ...road('private', 3, 5, [[100, 100], [190, 100]]), access: 'private' }];
  const options = {
    forwardMovements: [
      { via: 3, from: 'north', to: 'exit', turn: 'right', fromLanes: [0] },
      { via: 3, from: 'south', to: 'exit', turn: 'left', fromLanes: [0] },
      { via: 3, from: 'south', to: 'private', turn: 'right', fromLanes: [0] },
    ],
    signalApproachChains: ['north', 'south'].map(edge => ({ edges: [edge], stopOffset: 13 })),
  };
  const sharing = buildTrafficGraph([{ x: 0, z: 0, roads, junctions: [{ nodeId: 3, signalised: true }] }], options);
  assert.equal(sharing.edges.has('private'), false);
  assert.deepEqual(sharing.edges.get('south').forwardMovements[0].map(({ id }) => id), ['exit']);
  const traffic = createTraffic({ graph: sharing, maxVehicles: 0 });
  const near = { x: 100, z: 100 };
  traffic.update(29, near);
  const vehicles = [car(1, 'north', 40, 0), car(2, 'south', 40, 0)];
  traffic.vehicles.push(...vehicles);
  for (let step = 0; step < 16 * 60 && vehicles.some(({ edge }) => edge !== 'exit'); step++) {
    traffic.update(dt, near);
    const [a, b] = vehicles.map(vehicle => traffic.pose(vehicle));
    assert.ok(Math.hypot(a.x - b.x, a.z - b.z) >= sedan.length, 'the vehicles never overlap on the shared approach or exit');
    assert.ok(vehicles.filter(vehicle => vehicle.movement?.via === 3).length <= 1);
  }
  assert.ok(vehicles.every(({ edge, lane }) => edge === 'exit' && lane === 0));
});

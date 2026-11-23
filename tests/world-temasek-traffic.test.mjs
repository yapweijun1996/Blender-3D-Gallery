import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';

import { buildTrafficGraph, createTraffic, sampleEdge, VEHICLE_TYPES } from '../src/world/traffic.js';

const tile = JSON.parse(readFileSync(new URL('../models/world/tiles/-1_-6.json', import.meta.url), 'utf8'));
const routes = [
  ['21702431:4', '395443687:0', '750875319:0'],
  ['21701084:0', '395443688:0', '750875316:0'],
];
const near = { x: -136, z: -1368 };
const sedan = VEHICLE_TYPES.find(type => type.id === 'sedan');

function seed(id, edge, s, lane) {
  return { id, type: sedan, edge, s, lane, direction: 1, speed: 11, wait: 0 };
}

test('ordinary traffic uses both paved approaches and continues in its lane beneath Suntec City', () => {
  const graph = buildTrafficGraph([tile]);
  assert.deepEqual(graph.nodes.get(3983027173).forward, ['750875319:0', '753843011:0']);
  for (const route of routes) {
    assert.deepEqual(graph.edges.get(route[1]).forwardConnector, { id: route[2], lanes: [0, 1] });
    assert.ok(route.every(id => graph.edges.get(id).layer === 0));
  }

  for (const lane of [0, 1]) {
    // An ordinary random choice would take the second arm, the service driveway, at the north exit.
    const traffic = createTraffic({ graph, random: () => .99, maxVehicles: 0 });
    const vehicles = routes.map(([id], i) => seed(i + 1, id, graph.edges.get(id).length - 10, lane));
    traffic.vehicles.push(...vehicles);
    const visited = routes.map(() => new Set());
    let simultaneous = 0;
    for (let frame = 0; frame < 8 * 60 && traffic.vehicles.length; frame++) {
      traffic.update(1 / 60, near);
      if (vehicles.every((vehicle, index) => vehicle.edge === routes[index][1])) simultaneous++;
      for (const [index, vehicle] of vehicles.entries()) {
        const route = routes[index];
        if (visited[index].has(route[2])) continue;
        assert.ok(traffic.vehicles.includes(vehicle));
        assert.ok(route.includes(vehicle.edge), `unexpected transition to ${vehicle.edge}`);
        visited[index].add(vehicle.edge);
        assert.equal(vehicle.lane, lane);
        const pose = traffic.pose(vehicle);
        const center = sampleEdge(graph.edges.get(vehicle.edge), vehicle.s);
        const offset = (pose.x - center.x) * center.dz - (pose.z - center.z) * center.dx;
        assert.equal(pose.y, 0);
        assert.ok(Math.abs(offset - (.5 - lane) * 3.4) < 1e-6);
        if (vehicle.edge === route[2]) traffic.vehicles.splice(traffic.vehicles.indexOf(vehicle), 1);
      }
    }
    assert.ok(simultaneous > 100, 'both directions travel beneath the roof during the same frames');
    assert.deepEqual(visited.map(edges => [...edges]), routes);
  }
});

test('a missing northbound continuation keeps traffic clear of the unassessed driveway', () => {
  const [approach, under, exit] = routes[0];
  const roads = tile.roads.filter(road => road.id !== exit);
  const graph = buildTrafficGraph([{ ...tile, roads }]);
  assert.ok(graph.edges.has('753843011:0'));
  assert.equal(graph.edges.get(under).forwardConnector, null);
  const traffic = createTraffic({ graph, random: () => .99, maxVehicles: 0 });
  const vehicle = seed(1, approach, graph.edges.get(approach).length - 8, 0);
  traffic.vehicles.push(vehicle);
  for (let frame = 0; frame < 10 * 60; frame++) {
    traffic.update(1 / 60, near);
    assert.ok(traffic.vehicles.includes(vehicle));
    assert.ok(vehicle.edge === approach || vehicle.edge === under);
  }
  assert.equal(vehicle.edge, under);
  assert.equal(vehicle.speed, 0);
  assert.ok(graph.edges.get(under).length - vehicle.s >= sedan.length / 2 + .99);
});

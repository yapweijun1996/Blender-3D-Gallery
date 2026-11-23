import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';

import { buildTrafficGraph, createTraffic, sampleEdge, VEHICLE_TYPES } from '../src/world/traffic.js';

const tile = JSON.parse(readFileSync(new URL('../models/world/tiles/-2_-4.json', import.meta.url)));
const graph = buildTrafficGraph([tile]);
const through = ['723073393:0', '545362402:0', '545362402:1', '545362402:2', '545362403:0', '635373148:0'];
const incoming = '173791997:0';
const near = { x: -295, z: -935 };
const short = ['545362402:1', '545362403:0', '723073393:0'];

function car(id, edge, s, lane, typeId = 'sedan') {
  return { id, edge, s, lane, direction: 1, type: VEHICLE_TYPES.find(({ id }) => id === typeId), speed: graph.edges.get(edge).speed * .85 };
}

test('the regenerated route retains just the three reviewed sub-four-metre links', () => {
  assert.deepEqual([...graph.edges.values()].filter(edge => edge.length < 4).map(edge => edge.id).sort(), short);
  for (const id of short) assert.equal(graph.edges.get(id).retainShortTraffic, true);
  for (const id of ['736307184:1', '842958166:0']) {
    const road = tile.roads.find(edge => edge.id === id);
    assert.equal(road.retainShortTraffic, undefined);
    assert.equal(graph.edges.has(id), false);
  }
  assert.deepEqual(graph.nodes.get(6782303341).forward, ['172373834:0', '723073393:0']);
  assert.deepEqual(graph.nodes.get(12169571327).forward, ['545362402:1']);
  assert.deepEqual(graph.nodes.get(12169568595).backward, ['545362402:1']);
  for (const id of ['1314801325:0', '1314801304:0']) assert.equal(graph.edges.has(id), false);
});

test('through AI continues across both garage junctions on its original allowed lane at Y zero', () => {
  for (const [type, enteredLane, lane] of [['bus', 0, 0], ['sedan', 0, 1], ['sedan', 2, 2], ['sedan', 4, 4]]) {
    const traffic = createTraffic({ graph, random: () => .99, maxVehicles: 0 });
    const vehicle = car(1, incoming, 12, enteredLane, type);
    traffic.vehicles.push(vehicle);
    const visited = new Set();
    for (let i = 0; i < 360; i++) {
      traffic.update(1 / 60, near);
      assert.ok(traffic.vehicles.includes(vehicle));
      visited.add(vehicle.edge);
      if (vehicle.edge === incoming) continue;
      const pose = traffic.pose(vehicle);
      const center = sampleEdge(graph.edges.get(vehicle.edge), vehicle.s);
      assert.equal(vehicle.lane, lane);
      assert.equal(pose.y, 0);
      assert.ok(Math.abs((pose.x - center.x) * center.dz - (pose.z - center.z) * center.dx - (2 - lane) * 3.4) < 1e-6);
      if (vehicle.edge === through.at(-1)) break;
    }
    assert.deepEqual([...visited], [incoming, ...through]);
  }

  const turning = createTraffic({ graph, random: () => 0, maxVehicles: 0 });
  const vehicle = car(1, incoming, graph.edges.get(incoming).length - .1, 2);
  turning.vehicles.push(vehicle);
  turning.update(1 / 60, near);
  assert.equal(vehicle.edge, '172373834:0', 'the existing side road at the western junction remains a candidate');
});

test('frame overshoot crosses each reviewed short link and carries the exact residual distance', () => {
  const transitions = [
    [incoming, through[0], through[1]],
    [through[1], through[2], through[3]],
    [through[3], through[4], through[5]],
  ];
  for (const [from, stitch, to] of transitions) {
    const traffic = createTraffic({ graph, random: () => .99, maxVehicles: 0 });
    const vehicle = car(1, from, graph.edges.get(from).length - .1, 2);
    traffic.vehicles.push(vehicle);
    const dt = .5;
    const residual = vehicle.speed * dt - .1 - graph.edges.get(stitch).length;
    traffic.update(dt, near);
    assert.equal(vehicle.edge, to);
    assert.equal(vehicle.lane, 2);
    assert.ok(Math.abs(vehicle.s - residual) < 1e-9);
    assert.ok(vehicle.s > 0 && vehicle.s < graph.edges.get(to).length);
  }
});

test('a through driver slows for a same-lane leader beyond the short interior link', () => {
  const source = graph.edges.get(through[1]);
  const stitch = graph.edges.get(through[2]);
  const target = graph.edges.get(through[3]);
  const edges = new Map(graph.edges).set(target.id, { ...target, speed: 0 });
  const traffic = createTraffic({ graph: { ...graph, edges }, maxVehicles: 0 });
  const follower = car(1, source.id, 6, 2);
  const leader = { ...car(2, target.id, .5, 2), speed: 0 };
  traffic.vehicles.push(follower, leader);
  for (let i = 0; i < 360; i++) {
    traffic.update(1 / 60, near);
    assert.equal(follower.edge, source.id, 'the follower queues before the occupied short link');
    const bumperGap = source.length - follower.s + stitch.length + leader.s - (follower.type.length + leader.type.length) / 2;
    assert.ok(bumperGap > 1.85);
  }
  assert.ok(follower.speed < .1);
});

import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';

import { Box3 } from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { buildTrafficGraph, createTraffic, sampleEdge, VEHICLE_TYPES } from '../src/world/traffic.js';

const tile = JSON.parse(readFileSync(new URL('../models/world/tiles/-1_-4.json', import.meta.url), 'utf8'));
const graph = buildTrafficGraph([tile]);
const upstream = '479540200:2';
const approach = '649944021:0';
const passages = ['479745478:0', '479745478:1'];
const exit = '479745479:0';
const markedRoads = [approach, ...passages, exit, '479745479:1'];
const journey = [upstream, approach, ...passages, exit];
const roof = tile.buildings.find(({ id }) => id === 393090492);

function spawnTraffic(edgeId, lane, typeId, repeat = false) {
  const candidates = [...graph.edges.values()].filter(edge => edge.length > 25 && edge.class !== 'service' && edge.class !== 'footway');
  const edgeIndex = candidates.findIndex(({ id }) => id === edgeId);
  assert.ok(edgeIndex >= 0, `the source edge ${edgeId} supports ordinary spawns`);
  const edge = candidates[edgeIndex];
  const typeIndex = VEHICLE_TYPES.findIndex(({ id }) => id === typeId);
  assert.ok(typeIndex >= 0);
  const weigh = types => types.reduce((sum, type) => sum + type.weight, 0);
  const drawType = (weigh(VEHICLE_TYPES.slice(0, typeIndex)) + VEHICLE_TYPES[typeIndex].weight / 2) / weigh(VEHICLE_TYPES);
  const draws = [(edgeIndex + .5) / candidates.length, .5, (lane + .5) / edge.lanes, drawType];
  let index = 0;
  const random = () => draws[repeat ? index++ % draws.length : index++] ?? 0;
  const traffic = createTraffic({ graph, maxVehicles: 1, random });
  const mid = sampleEdge(edge, edge.length / 2);
  const near = { x: mid.x, z: mid.z + 100 };
  return { traffic, near, vehicle: traffic.spawn(near) };
}

function followJourney(type, initialLane, expectedLane) {
  const { traffic, near, vehicle } = spawnTraffic(upstream, initialLane, type);
  assert.deepEqual([vehicle.edge, vehicle.type.id, vehicle.lane], [upstream, type, initialLane]);
  const visited = new Map();
  for (let frame = 0; frame < 600; frame++) {
    traffic.update(1 / 60, near);
    assert.ok(traffic.vehicles.includes(vehicle));
    const edge = graph.edges.get(vehicle.edge);
    const pose = traffic.pose(vehicle);
    assert.equal(pose.y, 0, 'ordinary traffic follows the simulated level through both portals');
    if (edge.leftBusLane) {
      assert.equal(vehicle.lane, expectedLane);
      const center = sampleEdge(edge, vehicle.s);
      const leftOfCenter = (pose.x - center.x) * center.dz - (pose.z - center.z) * center.dx;
      assert.ok(Math.abs(leftOfCenter - (2 - expectedLane) * 3.4) < 1e-6);
    }
    if (!visited.has(vehicle.edge)) visited.set(vehicle.edge, vehicle.lane);
    if (vehicle.edge === exit) break;
  }
  assert.deepEqual([...visited], journey.map((id, index) => [id, index ? expectedLane : initialLane]));
}

test('the regenerated Raffles tile opens the five-lane chain and keeps the unverified service access out of traffic', () => {
  assert.deepEqual(tile.roads.filter(({ passageRoof }) => passageRoof === roof.id).map(({ id }) => id), passages);
  assert.deepEqual(tile.roads.filter(({ leftBusLane }) => leftBusLane).map(({ id }) => id).sort(), markedRoads.slice().sort());
  for (const id of markedRoads) {
    const edge = graph.edges.get(id);
    assert.deepEqual([edge.oneway, edge.lanes, edge.width, edge.leftBusLane], [true, 5, 17, true]);
  }
  for (const id of ['429052425:0', '1431080706:0']) {
    assert.ok(tile.roads.some(road => road.id === id && road.tunnel && !road.passageRoof));
    assert.equal(graph.edges.has(id), false);
  }
  assert.deepEqual(graph.nodes.get(7023019223).forward, ['479745478:1']);
  assert.deepEqual(graph.nodes.get(7023019223).backward, ['479745478:0']);
  for (const id of [upstream, '633871919:0']) {
    const edge = graph.edges.get(id);
    assert.deepEqual([edge.name, edge.oneway, edge.lanes, edge.width], ['Raffles Boulevard', true, 5, 17]);
    assert.equal(Boolean(edge.leftBusLane), false, 'the adjacent through road retains its ordinary lane rules');
  }
});

test('generated ordinary cars keep their chosen through lanes and cannot enter the left bus lane', () => {
  assert.equal(spawnTraffic(exit, 0, 'sedan', true).vehicle, null);
  assert.equal(spawnTraffic(exit, 1, 'sedan').vehicle.lane, 1);
  for (const lane of [1, 2, 3, 4]) followJourney('sedan', lane, lane);
  // The approach may receive lane-zero arrivals from the preceding ordinary road.
  followJourney('sedan', 0, 1);
});

test('a generated bus retains the left lane through both portals', () => {
  assert.equal(spawnTraffic(exit, 0, 'bus').vehicle.lane, 0);
  followJourney('bus', 0, 0);
});

test('the visible double-decker model fits beneath the modeled roof at road height', async t => {
  const asset = VEHICLE_TYPES.find(({ id }) => id === 'bus').model;
  const file = readFileSync(new URL(`../models/${asset}/${asset}.glb`, import.meta.url));
  const gltf = await new GLTFLoader().parseAsync(file.buffer.slice(file.byteOffset, file.byteOffset + file.byteLength), '');
  const bounds = new Box3().setFromObject(gltf.scene, true);
  assert.ok(Math.abs(bounds.min.y) < 1e-6);
  assert.ok(Math.abs(bounds.max.y - 4.4) < 1e-6);
  assert.equal(roof.minHeight, 4.5);
  assert.ok(bounds.max.y < roof.minHeight);
  t.diagnostic(`${bounds.max.y.toFixed(2)} m model top, ${(roof.minHeight - bounds.max.y).toFixed(2)} m clearance`);
});

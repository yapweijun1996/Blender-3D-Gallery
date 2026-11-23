import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { readFile } from 'node:fs/promises';
import test from 'node:test';
import { readFortCanningIntegration } from './fort-canning-integration.mjs';
import { readPinnedFortCanningTunnel } from './fort-canning-tunnel.mjs';

const route = await readFortCanningIntegration();
const crossing = (profile, id) => profile.crossings.find(({ edgeId }) => edgeId === id);
const points = route.fragments.flatMap(({ points }, index) => index ? points.slice(1) : points);
const near = (actual, expected, tolerance = 0.00001) => assert.ok(Math.abs(actual - expected) < tolerance, `${actual} vs ${expected}`);

function floorAt(station) {
  const upper = points.findIndex(point => point.s >= station);
  assert.ok(upper > 0, `station ${station} is in the drivable corridor`);
  const a = points[upper - 1], b = points[upper];
  return a.y + (b.y - a.y) * (station - a.s) / (b.s - a.s);
}

test('streamed Link profile regenerates offline and preserves the separate 361 m release', async () => {
  const prototype = await readPinnedFortCanningTunnel();
  assert.equal(await readFile(new URL('./fort-canning-integration.json', import.meta.url), 'utf8'), JSON.stringify(route) + '\n');
  assert.equal(prototype.length, 360.916499);
  assert.equal(route.simulation.originalTunnelLength, prototype.length);
  assert.equal(route.source.fixtureSha256, prototype.source.fixtureSha256);
  assert.equal(route.source.attribution, prototype.source.attribution);
  assert.equal(route.simulation.originalStartStation, -96);
  assert.equal(route.simulation.originalEndStation, 435.273987);
  assert.equal(route.length, 531.273987);
  assert.equal(route.width, 10.2);
  for (const { key, sha256 } of route.source.tiles) {
    const bytes = await readFile(new URL(`../../models/world/tiles/${key}.json`, import.meta.url));
    assert.equal(createHash('sha256').update(bytes).digest('hex'), sha256);
  }
  const { chain } = route.simulation;
  assert.deepEqual(chain.map(({ edgeId }) => edgeId), ['21815891:0', '21815891:1', '719635729:0', '719635728:0', '159677768:0', '39351292:0']);
  for (let i = 1; i < chain.length; i++) {
    assert.equal(chain[i].from, chain[i - 1].to);
    assert.equal(chain[i].start, chain[i - 1].end);
  }
  assert.equal(chain[2].tunnelTag, 'yes');
  assert.equal(chain[2].maxHeight, '4.5');
  assert.equal(chain[4].end - chain[4].start, prototype.length);
});

test('all four streamed pieces join at the same elevation and the grades stay within 8 percent', () => {
  assert.deepEqual(route.approaches.entry.at(-1), points[0]);
  assert.deepEqual(route.approaches.exit[0], points.at(-1));
  assert.ok(route.approaches.entry.every(({ y }) => y === 0));
  assert.equal(points[0].y, 0);
  assert.equal(points.at(-1).y, 0);
  assert.ok(points.some(({ y }) => y === -5.5));
  assert.deepEqual(route.fragments.map(({ tile }) => tile), [[-5, -6], [-6, -6], [-6, -7], [-7, -7]]);
  for (let i = 1; i < route.fragments.length; i++) {
    const previous = route.fragments[i - 1], next = route.fragments[i];
    const join = previous.points.at(-1);
    assert.deepEqual(next.points[0], join);
    assert.ok([join.x, join.z].some(coordinate => coordinate % route.tileSize === 0));
  }
  for (let index = 1; index < points.length; index++) {
    const a = points[index - 1], b = points[index];
    const run = b.s - a.s;
    assert.ok(run > 0 && run <= 1.000002);
    near(run, Math.hypot(a.x - b.x, a.z - b.z), 0.000003);
    assert.ok(Math.abs(b.y - a.y) / run <= 0.080004);
  }
  for (const s of Object.values(route.simulation.roof)) {
    assert.equal(points.find(point => point.s === s).y, -4.9);
  }
});

test('the full swept road widths preserve both target crossings at the surface', () => {
  const parking = crossing(route, '430502717:0');
  const road = crossing(route, '646730739:0');
  const existingCover = crossing(route, '723285353:0');
  assert.equal(parking.width, 3.4);
  assert.equal(road.width, 10.2);
  near(parking.at.s, 173.130203);
  near(road.at.s, 433.686294);
  assert.ok(road.end - road.start > 27.8, 'the full ribbon overlap is wider than the intersection on the Link centreline');
  assert.ok(parking.end - parking.start > parking.width);
  assert.deepEqual(existingCover.tiles, ['-6_-6', '-6_-7']);
  assert.ok(existingCover.points.some(([, z]) => z === -1500), 'the preserved road is joined across the production tile seam');
  for (const { kind, osmLayer, roofCovered, openCut, at, start, end } of [parking, road, existingCover]) {
    assert.equal(kind, 'road');
    assert.equal(osmLayer, 0);
    assert.equal(roofCovered, true);
    assert.deepEqual(openCut, []);
    assert.ok(at.s > start && at.s < end);
    for (const s of [start, at.s, end]) assert.ok(floorAt(s) < -4.9);
  }
});

test('the earlier descent protects inbound footways and park without opening the Stamford turn', async () => {
  const short = await readFortCanningIntegration({ start: -10 });
  const inbound = ['430502715:11', '175089156:9', '774912621:0', '774912620:0', '1236588331:0', '430502715:1'];
  for (const id of inbound) {
    const before = crossing(short, id), after = crossing(route, id);
    assert.equal(before.kind, 'pedestrian');
    assert.equal(before.width, 2.2);
    assert.ok(before.openCut.length > 0);
    assert.equal(after.roofCovered, true);
    assert.deepEqual(after.openCut, []);
    assert.deepEqual(after.points, before.points);
  }
  assert.ok(crossing(short, '16892550').openCut.length > 0);
  assert.equal(crossing(route, '16892550').roofCovered, true);
  assert.equal(crossing(route, '719635726').roofCovered, true);
  assert.ok(crossing(route, '1857318735').end < -4.95);
  assert.ok(crossing(route, '465064163:0').end < -13);
  const bridge = crossing(route, '719635727');
  assert.equal(bridge.bridge, 'yes');
  assert.equal(bridge.minHeight, null);
  assert.ok(bridge.openCut.length > 0);
  near(route.simulation.overheadBridge.minimumSimulatedUnderside, 2.441531);
  await assert.rejects(readFortCanningIntegration({ start: -40 }), /must start on the pinned surface approach/);
});

test('the Penang merge and uncovered footways keep default activation gated', () => {
  assert.deepEqual(route.simulation.gate.blockers, [
    { kind: 'building', edgeId: '719635727' },
    { kind: 'pedestrian', edgeId: '774912614:0' },
    { kind: 'pedestrian', edgeId: '1552288080:0' },
    { kind: 'road', edgeId: '654224115:0' },
  ]);
  const { flatExitConstraint, gate, onwardEdges, exitNodeId } = route.simulation;
  assert.equal(gate.ready, false);
  assert.deepEqual(onwardEdges, []);
  assert.equal(exitNodeId, 235180430);
  near(flatExitConstraint.run, 52.202618);
  near(flatExitConstraint.maximumLinearDepth, 4.176209);
  near(flatExitConstraint.shortfall, 0.723791);
  assert.ok(flatExitConstraint.maximumLinearDepth < flatExitConstraint.requiredDepth);
});

test('pinned official Penang ways prove the physical onward direction without adding them to the game graph', async () => {
  const { exitWitness, exitNodeId, onwardEdges, gate } = route.simulation;
  assert.equal(exitWitness.from, exitNodeId);
  assert.equal(exitWitness.retrievedOnUtc, '2026-11-23');
  assert.equal(exitWitness.attribution, route.source.attribution);
  assert.equal(exitWitness.to, 408999681);
  assert.equal(exitWitness.terminalSignal, true);
  near(exitWitness.length, 168.708755);
  assert.deepEqual(exitWitness.edges.map(edge => [edge.wayId, edge.from, edge.to]), [
    [888048852, 235180430, 1363263534], [74559749, 1363263534, 1363263510], [888048851, 1363263510, 408999681],
  ]);
  assert.deepEqual(exitWitness.edges.map(edge => [edge.version, edge.timestamp]), [
    [3, '2026-05-07T04:41:51Z'], [15, '2026-05-07T04:41:51Z'], [3, '2026-05-09T11:07:25Z'],
  ]);
  assert.deepEqual(exitWitness.edges[0].points[0], [points.at(-1).x, points.at(-1).z]);
  for (let i = 1; i < exitWitness.edges.length; i++) {
    assert.deepEqual(exitWitness.edges[i].points[0], exitWitness.edges[i - 1].points.at(-1));
  }
  for (const edge of exitWitness.edges) {
    assert.equal(edge.name, 'Penang Road');
    assert.equal(edge.lanes, 5);
    assert.equal(edge.oneway, true);
    assert.equal(edge.url, `https://api.openstreetmap.org/api/0.6/way/${edge.wayId}/full.json`);
  }
  const fixture = await readFile(new URL(`../../${exitWitness.sourceFixture}`, import.meta.url));
  assert.equal(createHash('sha256').update(fixture).digest('hex'), exitWitness.fixtureSha256);
  assert.ok(JSON.parse(fixture).elements.every(element =>
    ['uid', 'user', 'changeset'].every(key => !Object.hasOwn(element, key))));
  assert.deepEqual(onwardEdges, []);
  assert.equal(gate.ready, false);
});

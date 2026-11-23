import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import { gunzipSync } from 'node:zlib';

import { offsetPolyline } from '../../src/world/network/geometry.js';
import { buildTileFiles } from './build-tiles.mjs';
import { polylineLength } from './tile-geometry.mjs';

const source = JSON.parse(gunzipSync(readFileSync(new URL('./fixtures/marina-bay-2026-11-20.json.gz', import.meta.url))));
const tileName = '-2_-4.json';
const through = ['723073393:0', '545362402:0', '545362402:1', '545362402:2', '545362403:0', '635373148:0'];
const covered = through.slice(1, -1);
const short = ['723073393:0', '545362402:1', '545362403:0'];
const garageKerbs = ['1314801297:1', '1314801304:0', '1314801318:0', '1314801325:0', '1314816309:0', '1314816311:0'];
const { files } = buildTileFiles(source);
const compiled = JSON.parse(files.get(tileName));

function inside([x, z], ring) {
  return ring.slice(1).reduce((hit, [bx, bz], i) => {
    const [ax, az] = ring[i];
    return (az > z) !== (bz > z) && x < ax + (bx - ax) * (z - az) / (bz - az) ? !hit : hit;
  }, false);
}

function distanceToPolyline([x, z], points) {
  return Math.min(...points.slice(1).map(([bx, bz], i) => {
    const [ax, az] = points[i], dx = bx - ax, dz = bz - az;
    const fraction = Math.max(0, Math.min(1, ((x - ax) * dx + (z - az) * dz) / (dx * dx + dz * dz)));
    return Math.hypot(x - ax - dx * fraction, z - az - dz * fraction);
  }));
}

test('the pinned Marina Square ways compile one connected level passage and its mapped upper floor', () => {
  const checkedIn = readFileSync(new URL(`../../models/world/tiles/${tileName}`, import.meta.url), 'utf8');
  assert.equal(files.get(tileName), checkedIn);
  const tile = compiled;
  const roof = tile.buildings.find(({ id }) => id === 303311927);
  const edges = through.map(id => tile.roads.find(road => road.id === id));
  assert.deepEqual(tile.roadSurfaces.map(({ edges }) => edges), [through]);
  assert.deepEqual(tile.roads.filter(edge => edge.passageRoof === roof.id).map(({ id }) => id), covered);
  assert.deepEqual(edges.filter(edge => edge.retainShortTraffic).map(({ id }) => id), short);
  assert.ok(edges.every(edge => edge.lanes === 5 && edge.width === 17 && edge.oneway && edge.leftBusLane));
  assert.ok(Math.abs(edges.slice(1, -1).reduce((meters, edge) => meters + polylineLength(edge.geometry), 0) - 47.39) < .01);
  assert.equal(roof.height, 9.6);
  assert.equal(roof.minHeight, undefined, 'the bulk mall stays grounded');
  const [opening] = roof.passages;
  assert.equal(roof.passages.length, 1);
  assert.deepEqual([opening.floor, opening.soffit], [0, 4.5]);
  assert.deepEqual(opening.geometry[0], opening.geometry.at(-1));
  assert.ok(opening.geometry.every(point => point.every(value => value > 0 && value < 250)));
  assert.deepEqual(tile.pedestrian.filter(path => path.indoorLevel).map(path => [path.id, path.indoorLevel, path.floorHeight]),
    [['474174793:0', 1, 4.8], ['474174793:2', 1, 4.8]]);
  const upper = source.elements.find(element => element.type === 'way' && element.id === 474174793);
  assert.deepEqual([upper.tags.indoor, upper.tags.level, upper.tags.access], ['yes', '1', 'customers']);
  for (const id of ['1314801325:0', '1314801304:0']) {
    const garage = tile.roads.find(edge => edge.id === id);
    assert.equal(garage.access, 'destination');
    assert.equal(garage.tunnel, true);
    assert.equal(garage.passageRoof, undefined);
  }
  for (const [file, contents] of files) {
    if (file === tileName || file === 'index.json') continue;
    assert.ok(!contents.includes('"passageRoof":303311927'), `${file} has no Marina Square passage override`);
  }
});

test('only the pinned below-grade garage kerbs are masked on the through surface', () => {
  const tile = compiled;
  assert.deepEqual(tile.roadSurfaces.at(-1).subsurfaceKerbs, garageKerbs);
  for (const id of garageKerbs) {
    const road = tile.roads.find(edge => edge.id === id);
    const { tags } = source.elements.find(element => element.type === 'way' && element.id === road.wayId);
    assert.equal(tags.highway, 'service');
    assert.equal(tags.tunnel, 'yes');
    assert.equal(tags.access, 'destination');
    assert.ok(['driveway', 'parking_aisle'].includes(tags.service));
    assert.ok(Number(tags.layer) < 0);
    assert.equal(road.layer, Number(tags.layer));
    assert.ok(tile.kerbs.find(kerb => kerb.road === id && kerb.layer === road.layer));
  }
  const elements = source.elements.map(element => {
    if (element.type !== 'way' || element.id !== 1314816311) return element;
    const { layer, ...tags } = element.tags;
    return { ...element, tags };
  });
  const changed = JSON.parse(buildTileFiles(elements).files.get(tileName));
  assert.deepEqual(changed.roadSurfaces.at(-1).subsurfaceKerbs, garageKerbs.slice(0, -1),
    'an inferred layer alone does not support suppressing the kerb');
});

test('surface branch kerbs keep all exterior geometry along the extended through-road footprint', () => {
  const ids = ['173791997:0', ...through, '635373148:1'];
  const points = ids.flatMap((id, index) => compiled.roads.find(road => road.id === id).geometry.slice(index ? 1 : 0));
  const left = offsetPolyline(points, 8.5), right = offsetPolyline(points, -8.5);
  const roadRing = [...left, ...right.reverse(), left[0]];
  const changed = compiled.kerbs.filter(kerb => kerb.surfaceGeometry);
  const branches = ['172373834:0', '736307183:0', '1424403063:0'];
  assert.deepEqual(changed.map(({ road, side }) => [road, side]), branches.flatMap(id => [[id, 'left'], [id, 'right']]));
  for (const { geometry, surfaceGeometry, road, side } of changed) {
    assert.equal(surfaceGeometry.length, 1, 'the branch still has its exterior kerb');
    const [retained] = surfaceGeometry;
    assert.ok(retained.length >= 2);
    const label = `${road} ${side}`;
    const trimStart = distanceToPolyline(geometry[0], retained) > .001;
    assert.deepEqual(trimStart ? retained.at(-1) : retained[0], trimStart ? geometry.at(-1) : geometry[0], label);
    assert.ok(distanceToPolyline(trimStart ? retained[0] : retained.at(-1), roadRing) < .001, label);

    // A dense independent check measures both what remains and what was removed.
    for (const [index, end] of geometry.slice(1).entries()) {
      const start = geometry[index];
      for (let sample = 0; sample <= 250; sample++) {
        const point = start.map((value, axis) => value + (end[axis] - value) * sample / 250);
        if (distanceToPolyline(point, roadRing) < .001) continue;
        assert.equal(distanceToPolyline(point, retained) < .001, !inside(point, roadRing), label);
      }
    }
  }

  const westStripe = [182.4407, 52.9309];
  assert.equal(inside(westStripe, compiled.roadSurfaces[0].geometry), false);
  assert.equal(inside(westStripe, roadRing), true, 'the west extension clips the part before the short center stitch');
});

test('a changed motorcar or garage permission leaves the normal Marina Square tile intact', () => {
  const mutations = [
    [545362402, { motorcar: 'private', access: 'yes' }],
    [723073393, { access: 'destination' }],
    [1314801325, { access: 'yes' }],
  ];
  for (const [wayId, tags] of mutations) {
    const elements = source.elements.map(element => element.type === 'way' && element.id === wayId
      ? { ...element, tags: { ...element.tags, ...tags } }
      : element);
    const tile = JSON.parse(buildTileFiles(elements).files.get(tileName));
    assert.equal(tile.roadSurfaces, undefined, `unexpected passage at changed way ${wayId}`);
    assert.equal(tile.buildings.find(({ id }) => id === 303311927).passages, undefined);
    assert.ok(tile.roads.every(edge => !edge.passageRoof && !edge.retainShortTraffic));
    assert.ok(tile.pedestrian.every(path => path.indoorLevel === undefined));
    assert.deepEqual(tile.kerbs, compiled.kerbs.map(({ surfaceGeometry, ...original }) => original));
  }
});

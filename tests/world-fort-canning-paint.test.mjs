import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

import { buildTile } from "../src/world/tile-mesh.js";
import { buildTrafficGraph } from "../src/world/traffic.js";
import overlay from "../src/world/tunnel-integration/fort-canning-runtime-overlay.json" with { type: "json" };

const readTile = key => JSON.parse(readFileSync(new URL("../models/world/tiles/" + key + ".json", import.meta.url)));
const additions = ["roads", "kerbs", "junctions", "crossings"];

function overlayTile(key) {
  const base = readTile(key);
  const patch = overlay.tiles[key];
  return { ...base, ...Object.fromEntries(additions.map(layer => [layer, base[layer].concat(patch[layer])])) };
}

function atHeight(geometry, height) {
  const vertices = geometry.attributes.position.array;
  const y = Math.fround(height);
  const result = [];
  for (let offset = 0; offset < vertices.length; offset += 9) {
    if (vertices[offset + 1] === y && vertices[offset + 4] === y && vertices[offset + 7] === y) {
      result.push(...vertices.subarray(offset, offset + 9));
    }
  }
  return result;
}

function attributes(geometry) {
  return geometry && Object.fromEntries(Object.entries(geometry.attributes).map(([name, { array }]) => [name, array]));
}

test("empty optional paint controls preserve ordinary map geometry and source layers", () => {
  const tile = readTile("-5_-6");
  const ordinary = buildTile(tile);
  const selected = buildTile(tile, { paint: { roads: [], kerbs: [], pedestrian: [] }, visualOnly: {} });
  for (const shape of ["ground", "buildings", "towers"]) assert.deepEqual(attributes(selected[shape]), attributes(ordinary[shape]));
  for (const layer of ["solids", "bridgeSolids", "trees", "lamps", "busStops", "entrances"]) {
    assert.deepEqual(selected[layer], ordinary[layer]);
  }
});

test("the real Stamford markings and junction faces survive the tunnel road and kerb masks", () => {
  const tile = readTile("-5_-6");
  const oldLink = new Set(overlay.paint.roads);
  const ordinary = buildTile(tile).ground;
  const active = buildTile(tile, { paint: overlay.paint }).ground;
  const oldRoadStrips = tile.roads.filter(road => oldLink.has(road.id) && !road.tunnel);
  const removedRoadTriangles = oldRoadStrips.reduce((total, road) => total + (road.geometry.length - 1) * 2, 0);
  assert.ok(removedRoadTriangles > 0);
  assert.equal(atHeight(ordinary, .03).length - atHeight(active, .03).length, removedRoadTriangles * 9);
  assert.ok(atHeight(active, .12).length < atHeight(ordinary, .12).length);
  assert.deepEqual(atHeight(active, .032), atHeight(ordinary, .032));
  assert.ok(atHeight(ordinary, .06).length > 0);
  assert.deepEqual(atHeight(active, .06), atHeight(ordinary, .06));

  const withoutAnchors = buildTile({
    ...tile,
    roads: tile.roads.filter(road => !oldLink.has(road.id)),
  }).ground;
  assert.ok(atHeight(withoutAnchors, .06).length < atHeight(active, .06).length);
});

test("the authored walkway paint masks remove only the corresponding legacy paths", () => {
  const tile = overlayTile("-7_-7");
  const ordinary = buildTile(tile).ground;
  const active = buildTile(tile, { paint: overlay.paint }).ground;
  const maskedPaths = tile.pedestrian.filter(({ id }) => overlay.paint.pedestrian.includes(id));
  assert.equal(maskedPaths.length, 2);
  const removedPathTriangles = maskedPaths.reduce((total, path) => total + (path.geometry.length - 1) * 2, 0);
  assert.equal(atHeight(ordinary, .05).length - atHeight(active, .05).length, removedPathTriangles * 9);
  assert.ok(atHeight(active, .05).length > 0);
});

test("the real unmarked northern crossing has no paint while a null marking retains the fallback", () => {
  const northern = overlayTile("-8_-8");
  const [unmarked] = northern.crossings;
  assert.equal(unmarked.id, 1790403815);
  assert.equal(atHeight(buildTile(northern).ground, .06).length, 0);
  const fallback = buildTile({ ...northern, crossings: [{ ...unmarked, markings: null }] }).ground;
  assert.ok(atHeight(fallback, .06).length > 0);

  const western = overlayTile("-8_-7");
  const signalised = western.crossings.find(({ id }) => id === 2052788271);
  assert.equal(signalised.markings, null);
  assert.ok(atHeight(buildTile({ ...western, crossings: [signalised] }).ground, .06).length > 0);
});

test("private pavement and kerbs have no traffic edges or zebra references", () => {
  const key = "-8_-7", tile = overlayTile(key);
  const privateArm = overlay.tiles[key].visualOnly;
  const options = { paint: overlay.paint };
  const ordinary = buildTile(tile, options);
  const source = JSON.stringify(tile);
  // This private crossing falls within the old 4 m search radius of the public Penang Lane road.
  const privateCrossing = { id: 7888721864, point: [193.82, 91.68], roadId: "774912613:0" };
  const rendered = buildTile({
    ...tile,
    crossings: [...tile.crossings, privateCrossing],
  }, { ...options, visualOnly: { ...privateArm, crossings: [privateCrossing] } });
  assert.ok(atHeight(rendered.ground, .03).length > atHeight(ordinary.ground, .03).length);
  assert.ok(atHeight(rendered.ground, .12).length > atHeight(ordinary.ground, .12).length);
  assert.deepEqual(atHeight(rendered.ground, .06), atHeight(ordinary.ground, .06));
  assert.deepEqual(rendered.solids, ordinary.solids);
  assert.equal(JSON.stringify(tile), source);
  const graph = buildTrafficGraph([tile]);
  for (const { id } of privateArm.roads) assert.ok(!graph.edges.has(id));
});

test("the paint masks preserve source bridge solids and visual-only decks add no solids", () => {
  const bridge = {
    id: "bridge",
    bridge: true,
    layer: 1,
    width: 6.8,
    edgeStart: 0,
    edgeLength: 160,
    geometry: [[0, 0], [80, 0], [160, 0]],
  };
  const tile = { x: 0, z: 0, roads: [bridge] };
  const mapped = buildTile(tile);
  const hidden = buildTile(tile, { paint: { roads: [bridge.id] } });
  assert.equal(mapped.bridgeSolids.length, 1);
  assert.equal(hidden.ground, null);
  assert.deepEqual(hidden.bridgeSolids, mapped.bridgeSolids);

  const visual = buildTile({ x: 0, z: 0 }, { visualOnly: { roads: [bridge] } });
  assert.deepEqual(attributes(visual.ground), attributes(mapped.ground));
  assert.deepEqual(visual.bridgeSolids, []);
});

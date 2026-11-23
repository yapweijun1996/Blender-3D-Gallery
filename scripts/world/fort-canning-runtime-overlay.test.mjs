import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import test from "node:test";

import { buildFortCanningRuntimeOverlay } from "./fort-canning-runtime-overlay.mjs";
import { buildTrafficGraph } from "../../src/world/traffic.js";

const output = new URL("../../src/world/tunnel-integration/fort-canning-runtime-overlay.json", import.meta.url);
const overlay = JSON.parse(readFileSync(output));
const layers = ["roads", "kerbs", "junctions", "crossings"];
const readBase = key => readFileSync(new URL("../../models/world/tiles/" + key + ".json", import.meta.url));

function publicTile(base, key) {
  const additions = overlay.tiles[key];
  return { ...base, ...Object.fromEntries(layers.map(layer => [layer, base[layer].concat(additions[layer])])) };
}

test("the runtime overlay regenerates byte for byte from the pinned junction and the three tracked tiles", async () => {
  assert.equal(JSON.stringify(await buildFortCanningRuntimeOverlay()) + "\n", readFileSync(output, "utf8"));
  assert.deepEqual(Object.keys(overlay.tiles), ["-8_-8", "-8_-7", "-7_-7"]);
  assert.deepEqual(overlay.requiredTiles, ["-5_-6", "-6_-6", "-6_-7", "-7_-7", "-8_-7", "-8_-8"]);
  for (const key of Object.keys(overlay.tiles)) {
    const bytes = readBase(key);
    assert.equal(overlay.tiles[key].baseSha256, createHash("sha256").update(bytes).digest("hex"));
    const base = JSON.parse(bytes);
    const combined = publicTile(base, key);
    for (const field of Object.keys(base)) {
      if (layers.includes(field)) assert.deepEqual(combined[field].slice(0, base[field].length), base[field]);
      else assert.deepEqual(combined[field], base[field]);
    }
  }
});

test("the public additions keep the six directed movements and full signal approach chains", () => {
  const tiles = Object.keys(overlay.tiles).map(key => publicTile(JSON.parse(readBase(key)), key));
  const signalApproachChains = overlay.signalApproaches.map(({ edges }) => ({ edges, stopOffset: 10 }));
  const graph = buildTrafficGraph(tiles, { signalApproachChains });
  assert.deepEqual(overlay.movements.map(({ via, from, to, fromLanes }) => [via, from, to, fromLanes]), [
    [408999681, "888048851:2", "75551640:0", [0, 1, 2, 3, 4]],
    [408999681, "474300998:5", "75551640:0", [0, 1, 2]],
    [408999681, "666009287:1", "75551640:0", [0, 1]],
    [6097184849, "75551640:0", "649770884:0", [0, 1, 2, 3, 4]],
    [1275666711, "649770884:0", "112154347:0", [0, 1]],
    [1275666711, "649770884:0", "173767817:0", [1, 2, 3, 4]],
  ]);
  for (const { via, from, to } of overlay.movements) {
    assert.equal(graph.edges.get(from).to, via);
    assert.equal(graph.edges.get(to).from, via);
  }
  assert.deepEqual(overlay.signalApproaches, [
    { signal: 6176417027, edges: ["74559749:0"] },
    { signal: 408999681, edges: ["888048851:0", "888048851:2"] },
    { signal: 408999681, edges: ["474300998:0", "474300998:5"] },
    { signal: 408999681, edges: ["666009287:0", "666009287:1"] },
  ]);
  assert.equal(graph.edges.get("888048851:0").forwardSignal.approach.terminal, "888048851:2");
  assert.deepEqual(graph.nodes.get(408999681).forward, ["75551640:0"]);
  assert.ok([...graph.edges.keys()].every(id => !id.startsWith("774912613:")));
  const privateArm = overlay.tiles["-8_-7"].visualOnly;
  assert.deepEqual(privateArm.roads.map(({ id }) => id), ["774912613:0", "774912613:1", "774912613:3"]);
  assert.ok(privateArm.roads.every(({ layer, access }) => layer === 0 && access === "private"));
  assert.ok(privateArm.kerbs.every(({ road }) => privateArm.roads.some(({ id }) => id === road)));
});

test("the active paint masks retain the road references, entry junctions and pedestrian data", () => {
  const legacyRoads = ["21815891:0", "21815891:1", "719635729:0", "719635728:0", "159677768:0", "39351292:0", "654224115:0"];
  const trunk = ["74559749:0", "74559749:1", "888048851:0", "888048851:2", "888048852:0"];
  assert.deepEqual(overlay.paint, {
    roads: [...legacyRoads, ...trunk],
    kerbs: legacyRoads,
    pedestrian: ["774912614:0", "1552288080:0"],
  });
  const entry = JSON.parse(readBase("-5_-6"));
  const anchor = entry.roads.find(({ id }) => id === "21815891:0").geometry.at(-1);
  const zebra = entry.crossings.find(({ id }) => id === 1857318735);
  const path = entry.crossings.find(({ id }) => id === "189017873:0");
  assert.deepEqual(zebra.point, anchor);
  assert.deepEqual(path.geometry.at(-1), anchor);
  for (const nodeId of [1857318735, 232353329]) assert.ok(entry.junctions.some(junction => junction.nodeId === nodeId));
  const exit = publicTile(JSON.parse(readBase("-7_-7")), "-7_-7");
  for (const id of overlay.paint.pedestrian) assert.ok(exit.pedestrian.some(path => path.id === id));
  for (const id of trunk) {
    assert.ok(Object.values(overlay.tiles).some(tile => tile.roads.some(road => road.id === id)));
    assert.ok(Object.values(overlay.tiles).some(tile => tile.kerbs.some(kerb => kerb.road === id)));
  }
});

test("crossing markings stay explicit and every added public crossing keeps its owning road", () => {
  const north = overlay.tiles["-8_-8"];
  const west = overlay.tiles["-8_-7"];
  assert.deepEqual(north.crossings, [
    { id: 1790403815, point: [224.69, 242.88], roadId: "474300998:0", markings: false, signalised: false },
  ]);
  const crossing = west.crossings.find(({ id }) => id === 2052788271);
  assert.deepEqual(crossing, { id: 2052788271, point: [200.53, 67.05], roadId: "474300998:0", markings: null, signalised: true });
  assert.ok(JSON.parse(readBase("-8_-7")).pedestrian.find(({ id }) => id === "194775119:0").geometry.some(point =>
    point[0] === crossing.point[0] && point[1] === crossing.point[1]));
  assert.equal(west.crossings.find(({ id }) => id === 1790374540).markings, true);
  assert.ok(west.crossings.every(({ id, roadId }) =>
    west.roads.some(road => road.id === roadId && (road.from === id || road.to === id))));
  assert.ok(west.crossings.every(({ id }) => id !== 7888721864 && id !== 7888937656));
});

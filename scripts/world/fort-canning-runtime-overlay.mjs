import { createHash, randomUUID } from "node:crypto";
import { readFile, rename, rm, writeFile } from "node:fs/promises";
import { pathToFileURL } from "node:url";

import { buildTileFiles, MAX_TILE_BYTES } from "./build-tiles.mjs";
import profile from "./fort-canning-integration.json" with { type: "json" };
import { readFortCanningJunction } from "./fort-canning-junction.mjs";

const BASE_TILES = new URL("../../models/world/tiles/", import.meta.url);
const OUTPUT = new URL("../../src/world/tunnel-integration/fort-canning-runtime-overlay.json", import.meta.url);
const PRIVATE_ARM = 774912613;
const layerKeys = {
  roads: ({ id }) => id,
  kerbs: ({ road, side }) => road + ":" + side,
  junctions: ({ nodeId }) => nodeId,
  crossings: ({ id }) => id,
};

function crossingMetadata(marker, tags, roads) {
  // Keep a marker on its mapped road, even when a different carriageway passes nearby.
  const road = roads.find(({ to }) => to === marker.id) ?? roads.find(({ from }) => from === marker.id);
  if (!road) throw new Error("Missing public road for crossing " + marker.id);
  const marking = tags["crossing:markings"];
  const markings = marking === "no" || tags.crossing === "unmarked" ? false
    : marking === "yes" || tags.crossing === "marked" ? true
    : null;
  const signalised = marker.signalised || tags["crossing:signals"] === "yes" || tags.crossing === "traffic_signals";
  return { ...marker, roadId: road.id, markings, signalised };
}

function privateArmTiles(witness) {
  const way = witness.ways.get(PRIVATE_ARM);
  if (way?.tags.access !== "private") throw new Error("Missing private Penang Lane spur");
  const nodes = new Set(way.nodes);
  const { files, index } = buildTileFiles([way, ...witness.fixture.elements.filter(element => element.type === "node" && nodes.has(element.id))]);
  return new Map(index.tiles.map(({ file }) => {
    const { roads, kerbs } = JSON.parse(files.get(file));
    // Private markers must not snap across to a public road in the zebra painter.
    return [file, { roads, kerbs }];
  }));
}

function publicSignalEdges(roads, { signal, wayId }) {
  const approaches = new Map(roads.filter(road => road.wayId === wayId).map(road => [road.to, road]));
  const edges = [];
  for (let approach = approaches.get(signal); approach; approach = approaches.get(approach.from)) {
    edges.unshift(approach.id);
    approaches.delete(approach.to);
  }
  if (!edges.length) throw new Error("Missing signal approach for OSM node " + signal);
  return { signal, edges };
}

function publicMovement(roads, { via, from, to, turn, fromLanes }) {
  const incoming = roads.find(road => road.wayId === from && road.to === via);
  const outgoing = roads.find(road => road.wayId === to && road.from === via);
  if (!incoming || !outgoing) throw new Error("Missing public movement at OSM node " + via);
  return { via, from: incoming.id, to: outgoing.id, turn, fromLanes };
}

function checkBaseTile(base, additional, file) {
  const combined = { ...base };
  for (const [layer, key] of Object.entries(layerKeys)) {
    const present = new Set(base[layer].map(key));
    const incoming = additional[layer].concat(additional.visualOnly?.[layer] ?? []);
    if (incoming.some(feature => present.has(key(feature)))) {
      throw new Error("An overlay " + layer + " ID already exists in " + file);
    }
    combined[layer] = base[layer].concat(incoming);
  }
  if (Buffer.byteLength(JSON.stringify(combined)) >= MAX_TILE_BYTES) {
    throw new Error("The combined tile exceeds the world byte limit: " + file);
  }
}

/** Build the local overlay from pinned sources. Base tile arrays and their paint references stay intact. */
export async function buildFortCanningRuntimeOverlay() {
  const witness = await readFortCanningJunction();
  const privateTiles = privateArmTiles(witness);
  const tagsByNode = new Map(witness.fixture.elements.filter(({ type }) => type === "node").map(({ id, tags }) => [id, tags]));
  const roads = [...witness.roadFragments.values()].map(([piece]) => piece.road);

  const tiles = Object.fromEntries(await Promise.all([...witness.tiles].map(async ([file, tile]) => {
    const bytes = await readFile(new URL(file, BASE_TILES));
    const base = JSON.parse(bytes);
    if (base.x !== tile.x || base.z !== tile.z) throw new Error("Unexpected base tile origin: " + file);
    const visualOnly = privateTiles.get(file);
    const additional = {
      baseSha256: createHash("sha256").update(bytes).digest("hex"),
      roads: tile.roads,
      kerbs: tile.kerbs,
      junctions: tile.junctions,
      crossings: tile.crossings.map(crossing => crossingMetadata(crossing, tagsByNode.get(crossing.id), tile.roads)),
      ...(visualOnly ? { visualOnly } : {}),
    };
    checkBaseTile(base, additional, file);
    return [tile.x + "_" + tile.z, additional];
  })));

  const legacyRoads = [...profile.simulation.chain.map(({ edgeId }) => edgeId), "654224115:0"];
  const trunk = new Set(profile.simulation.exitWitness.edges.map(({ wayId }) => wayId));
  const weldedExitRoads = roads.filter(({ wayId }) => trunk.has(wayId)).map(({ id }) => id).sort();
  return {
    requiredTiles: [...new Set([...profile.fragments.map(({ tile }) => tile.join("_")), ...Object.keys(tiles).reverse()])],
    tiles,
    paint: {
      // Skip the ribbons in the paint pass only. The base and new road records locate crossings.
      roads: legacyRoads.concat(weldedExitRoads),
      kerbs: legacyRoads,
      pedestrian: ["774912614:0", "1552288080:0"],
    },
    movements: witness.movements.map(movement => publicMovement(roads, movement)),
    signalApproaches: witness.signalApproaches.map(approach => publicSignalEdges(roads, approach)),
  };
}

if (process.argv[1] && pathToFileURL(process.argv[1]).href === import.meta.url) {
  const data = JSON.stringify(await buildFortCanningRuntimeOverlay()) + "\n";
  const temporary = new URL(OUTPUT.href + "." + randomUUID() + ".tmp");
  try {
    await writeFile(temporary, data, { flag: "wx" });
    await rename(temporary, OUTPUT);
  } finally {
    await rm(temporary, { force: true });
  }
}

import { createHash } from "node:crypto";
import { readFile } from "node:fs/promises";

import { projectOsm } from "../../src/world/network/project.js";
import { buildTileFiles } from "./build-tiles.mjs";

const FIXTURE = new URL("./fixtures/fort-canning-penang-junction-2026-11-23.json", import.meta.url);
const FIXTURE_SHA256 = "9b6406380f1d862576a957069b5b3281aa3c6b6073b769fa25530691b0814a73";
const EXIT_FIXTURE = new URL("./fixtures/fort-canning-penang-exit-2026-11-23.json", import.meta.url);
const THROUGH = "through";
const TERMINAL_SIGNAL = 408999681;
const FIRST_FORK = 1275666711;
const PUBLIC_ACCESS = new Set(["yes", "designated", "permissive"]);
const sha = bytes => createHash("sha256").update(bytes).digest("hex");
const elementKey = ({ type, id }) => type + ":" + id;

function supportsPublicCars({ tags }) {
  const access = tags.motorcar ?? tags.motor_vehicle ?? tags.vehicle ?? tags.access;
  return tags.oneway === "yes" && (!access || PUBLIC_ACCESS.has(access));
}

function laneIndications(way) {
  const lanes = Number(way.tags.lanes);
  const indications = way.tags["turn:lanes"]?.split("|").map(lane => lane.split(";"));
  if (!Number.isInteger(lanes) || lanes < 1 || (indications && indications.length !== lanes)) {
    throw new Error("Invalid lane count for OSM way " + way.id);
  }
  return indications ?? Array.from({ length: lanes }, () => [THROUGH]);
}

function movement(ways, restrictions, via, from, to, turn) {
  const approach = ways.get(from), departure = ways.get(to);
  if (approach?.nodes.at(-1) !== via || departure?.nodes[0] !== via ||
      !supportsPublicCars(approach) || !supportsPublicCars(departure)) {
    throw new Error("The movement is missing a directed public approach or exit at OSM node " + via);
  }
  for (const restriction of restrictions) {
    const members = new Map(restriction.members.map(({ role, ref }) => [role, ref]));
    if (members.get("via") !== via || members.get("from") !== from) continue;
    const prohibited = restriction.tags.restriction.startsWith("only_")
      ? members.get("to") !== to
      : members.get("to") === to;
    if (prohibited) throw new Error("The movement conflicts with OSM restriction " + restriction.id);
  }
  const fromLanes = laneIndications(approach).flatMap((indications, lane) => indications.includes(turn) ? [lane] : []);
  if (!fromLanes.length) throw new Error("No source lane permits the movement from OSM way " + from);
  return { via, from, to, turn, fromLanes };
}

function getSignalApproaches(nodes, ways, signal, sources) {
  const node = nodes.get(signal);
  if (node?.tags?.highway !== "traffic_signals") throw new Error("Missing OSM signal " + signal);
  return sources.map(wayId => {
    const way = ways.get(wayId);
    const end = way.nodes.indexOf(signal);
    if (end < 1 || !supportsPublicCars(way)) throw new Error("Missing directed approach to OSM signal " + signal);
    // Include the full approach even when a crossing splits the final few metres into another graph edge.
    return { signal, wayId, points: way.nodes.slice(0, end + 1).map(id => projectOsm(nodes.get(id))) };
  });
}

function verifyEvidence(fixture) {
  const elements = new Map(fixture.elements.map(element => [elementKey(element), element]));
  const cited = new Set();
  for (const request of fixture.requests) {
    const selected = request.elements.map(key => elements.get(key));
    if (selected.some(element => !element) || sha(JSON.stringify(selected)) !== request.elementsSha256) {
      throw new Error("The selected elements no longer match " + request.url);
    }
    for (const key of request.elements) cited.add(key);
  }
  if (cited.size !== elements.size) throw new Error("The junction fixture contains uncited elements");
}

function collectRoadFragments(tiles) {
  const fragments = new Map();
  for (const [file, tile] of tiles) {
    for (const road of tile.roads) {
      const pieces = fragments.get(road.id) ?? [];
      pieces.push({ file, road });
      fragments.set(road.id, pieces);
    }
  }
  return fragments;
}

/** An edge is usable once all its expected directed fragments match the loaded tile data. */
export function isFortCanningJunctionEdgeReady(witness, edgeId, loadedTiles) {
  const fragments = witness.roadFragments.get(edgeId);
  return Boolean(fragments?.every(({ file, road }) => loadedTiles.get(file)?.roads?.some(candidate =>
    candidate.id === edgeId && candidate.from === road.from && candidate.to === road.to &&
    candidate.oneway === road.oneway && candidate.lanes === road.lanes &&
    candidate.geometry?.length === road.geometry.length &&
    candidate.geometry.every(([x, z], index) => x === road.geometry[index][0] && z === road.geometry[index][1]))));
}

/** Verify the pinned junction evidence and derive a local public-road overlay without writing tiles. */
export async function readFortCanningJunction() {
  const [fixtureBytes, exitBytes] = await Promise.all([readFile(FIXTURE), readFile(EXIT_FIXTURE)]);
  if (sha(fixtureBytes) !== FIXTURE_SHA256) throw new Error("The pinned Penang junction SHA-256 changed");
  const fixture = JSON.parse(fixtureBytes);
  verifyEvidence(fixture);
  const exit = JSON.parse(exitBytes);
  const elements = new Map(exit.elements.map(element => [elementKey(element), element]));
  for (const element of fixture.elements) {
    const key = elementKey(element), previous = elements.get(key);
    if (previous && (previous.version !== element.version || previous.lat !== element.lat || previous.lon !== element.lon ||
        JSON.stringify(previous.nodes) !== JSON.stringify(element.nodes))) {
      throw new Error("The new evidence does not align with the pinned exit at " + key);
    }
    elements.set(key, element);
  }

  const source = [...elements.values()];
  const ways = new Map(source.filter(({ type }) => type === "way").map(way => [way.id, way]));
  const nodes = new Map(source.filter(({ type }) => type === "node").map(node => [node.id, node]));
  const restrictions = source.filter(element => element.type === "relation" && element.tags.type === "restriction");
  const movements = [
    movement(ways, restrictions, TERMINAL_SIGNAL, 888048851, 75551640, THROUGH),
    movement(ways, restrictions, TERMINAL_SIGNAL, 474300998, 75551640, "right"),
    movement(ways, restrictions, TERMINAL_SIGNAL, 666009287, 75551640, "left"),
    movement(ways, restrictions, 6097184849, 75551640, 649770884, THROUGH),
    movement(ways, restrictions, FIRST_FORK, 649770884, 112154347, "left"),
    movement(ways, restrictions, FIRST_FORK, 649770884, 173767817, THROUGH),
  ];
  const forkTurns = new Set(movements.filter(({ via }) => via === FIRST_FORK).map(({ turn }) => turn));
  const unresolvedForkLanes = laneIndications(ways.get(649770884)).flatMap((indications, lane) =>
    indications.filter(turn => !forkTurns.has(turn)).map(turn => ({ lane, turn })));
  const signalApproaches = [
    ...getSignalApproaches(nodes, ways, 6176417027, [74559749]),
    ...getSignalApproaches(nodes, ways, TERMINAL_SIGNAL, [888048851, 474300998, 666009287]),
  ];

  const publicWays = [...ways.values()].filter(supportsPublicCars);
  const publicNodeIds = new Set(publicWays.flatMap(way => way.nodes));
  const { files, index } = buildTileFiles([...publicWays, ...[...publicNodeIds].map(id => nodes.get(id))]);
  const tiles = new Map(index.tiles.map(({ file }) => [file, JSON.parse(files.get(file))]));
  return { fixture, ways, movements, restrictions, unresolvedForkLanes, signalApproaches, tiles, roadFragments: collectRoadFragments(tiles) };
}

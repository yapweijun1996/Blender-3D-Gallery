// Traffic on the mapped road network: vehicles follow road edges on the left lane, keep a gap to the car ahead,
// choose a road at each junction and stop at red signals. Pure logic (no rendering), driven by update(dt).
// Roads come from the map tiles (models/world/tiles); an edge is stitched together from its per-tile fragments.

import { bridgeHeight, isBridge } from "./bridges.js";

export const LANE = 3.4;
const SIGNAL = { green: 24, amber: 3, clear: 2 }; // seconds; two phases take turns
const STUCK_SECONDS = 45;
const SIGNAL_CYCLE = 2 * (SIGNAL.green + SIGNAL.amber + SIGNAL.clear);
export const VEHICLE_TYPES = [
  { id: "sedan", weight: 5, length: 4.4, width: 1.8, model: "car_saga" },
  { id: "hatchback", weight: 4, length: 3.9, width: 1.7, model: "car_hatchback_hd" },
  { id: "taxi", weight: 3, length: 4.6, width: 1.8, model: "sg-taxi-hd" },
  { id: "bus", weight: 2, length: 11.5, width: 2.5, model: "sg-bus-double-hd" },
  { id: "lorry", weight: 1, length: 7.5, width: 2.4, model: "sg-lorry-hd" },
  { id: "police", weight: 0.4, length: 4.6, width: 1.8, model: "sg-police-hd" },
  { id: "ambulance", weight: 0.3, length: 5.4, width: 2.0, model: "sg-ambulance-hd" },
  { id: "school-bus", weight: 0.4, length: 8.5, width: 2.4, model: "sg-school-bus-hd" },
];

const distance = (a, b) => Math.hypot(a[0] - b[0], a[1] - b[1]);
const close = (a, b) => distance(a, b) < 0.06; // tile fragments meet on shared border points rounded to a centimetre
const oneWayLaneOffset = (count, lane) => (count / 2 - lane - 0.5) * LANE;

function polylineLength(points) {
  let total = 0;
  for (let i = 1; i < points.length; i++) total += distance(points[i - 1], points[i]);
  return total;
}

/**
 * Stitch fragments (already in travel order) end to end into one polyline, or the longest chain when gaps remain.
 * A fragment is { points, start } where start is how far along the whole edge it begins (bridges only, else 0);
 * the chain keeps the start of its first fragment.
 */
function chain(fragments) {
  const remaining = fragments.map(fragment => ({ points: fragment.points.slice(), start: fragment.start }));
  const chains = [];
  while (remaining.length) {
    let current = remaining.shift(), grew = true;
    while (grew) {
      grew = false;
      for (let i = 0; i < remaining.length; i++) {
        if (close(current.points.at(-1), remaining[i].points[0])) { current = { points: current.points.concat(remaining.splice(i, 1)[0].points.slice(1)), start: current.start }; grew = true; break; }
        if (close(remaining[i].points.at(-1), current.points[0])) { const before = remaining.splice(i, 1)[0]; current = { points: before.points.concat(current.points.slice(1)), start: before.start }; grew = true; break; }
      }
    }
    chains.push(current);
  }
  return chains.sort((a, b) => polylineLength(b.points) - polylineLength(a.points))[0];
}

function offsetLane(at, offset) {
  return [at.x - (at.rx ?? -at.dz) * offset, at.z - (at.rz ?? at.dx) * offset];
}

function lanesMeet(source, destination, lanes) {
  const end = sampleEdge(source, source.length), start = sampleEdge(destination, 0);
  if (end.dx * start.dx + end.dz * start.dz < .999) return false;
  if (Math.abs((end.y ?? 0) - (start.y ?? 0)) > .06) return false;
  return lanes.every((lane, index) => close(
    offsetLane(end, oneWayLaneOffset(source.lanes, index)),
    offsetLane(start, oneWayLaneOffset(destination.lanes, lane)),
  ));
}

function configureForwardConnectors(edges, nodes, connectors) {
  const possibleMerges = new Set();
  for (const [id, connector] of connectors) {
    const edge = edges.get(id);
    if (!edge) continue;
    // Keep the configured route closed while its successor is unavailable in the loaded graph.
    edge.forwardConnector = null;
    const next = edges.get(connector?.id);
    const lanes = connector?.lanes;
    if (!edge.oneway || !next?.oneway || next === edge || edge.to !== next.from || !Array.isArray(lanes) ||
        lanes.length !== edge.lanes || new Set(lanes).size !== lanes.length ||
        [...lanes].some(lane => !Number.isInteger(lane) || lane < 0 || lane >= next.lanes)) continue;
    edge.forwardConnector = { id: next.id, lanes: lanes.slice() };
    possibleMerges.add(edge.to);
  }

  for (const id of possibleMerges) {
    const node = nodes.get(id);
    if (node.forward.length !== 1 || node.backward.length < 2) continue;
    const next = edges.get(node.forward[0]);
    const incoming = node.backward.map(edgeId => edges.get(edgeId));
    if (!incoming.every(edge => edge.forwardConnector?.id === next.id && lanesMeet(edge, next, edge.forwardConnector.lanes))) continue;
    const lanes = incoming.flatMap(edge => edge.forwardConnector.lanes);
    if (lanes.length === next.lanes && new Set(lanes).size === lanes.length) node.laneDisjointMerge = true;
  }
}

function configureSignalApproachChains(edges, nodes, signalised, chains) {
  for (const chain of chains) {
    const { edges: ids, stopOffset } = chain ?? {};
    if (!Array.isArray(ids) || !ids.length || new Set(ids).size !== ids.length ||
        !Number.isFinite(stopOffset) || stopOffset <= 0) continue;
    const route = Array.from(ids, id => edges.get(id));
    if (!route.every(edge => edge?.oneway)) continue;
    const terminal = route.at(-1);
    if (!signalised.has(terminal.to)) continue;
    // The earlier signal still controls traffic on its own approach.
    const priorSignal = route.findLastIndex(edge => edge !== terminal && signalised.has(edge.to));
    if (!route.slice(0, -1).every((edge, index) => {
      const next = route[index + 1];
      const joined = edge.to === next.from && close(edge.points.at(-1), next.points[0]);
      if (!joined) return false;
      if (index <= priorSignal) return true;
      if (edge.forwardConnector !== undefined) return edge.forwardConnector?.id === next.id;
      const node = nodes.get(edge.to);
      return node.forward.length === 1 && node.backward.every(id => edges.get(id).oneway);
    })) continue;

    const sections = route.slice(priorSignal + 1);
    let toLine = sections.reduce((length, edge) => length + edge.length, 0) - stopOffset;
    if (toLine < 0 || sections.some(edge => edge.forwardSignal)) continue;
    const { dx, dz } = sampleEdge(terminal, terminal.length);
    const approach = { terminal: terminal.id, bearing: { dx, dz }, phase: phaseOf(dx, dz) };
    for (const edge of sections) {
      if (!approach.line && toLine <= edge.length) {
        approach.line = { ...sampleEdge(edge, toLine), width: edge.width };
      }
      edge.forwardSignal = { approach, toLine };
      toLine -= edge.length;
    }
  }
}

const ENTRY_BLEND = 6;
const PUBLIC_ACCESS = new Set([null, undefined, 'yes', 'designated', 'permissive']);
const clearingDistance = length => ENTRY_BLEND + length / 2 + 1;
const SPAWN_CLEARANCE = Math.max(...VEHICLE_TYPES.map(({ length }) => clearingDistance(length)));

function movementCurve(source, target, fromLane, toLane) {
  const enter = source.length - Math.min(ENTRY_BLEND, source.length * .45);
  const exit = Math.min(ENTRY_BLEND, target.length * .45);
  const start = sampleEdge(source, enter), end = sampleEdge(target, exit);
  const [ax, az] = offsetLane(start, oneWayLaneOffset(source.lanes, fromLane));
  const [bx, bz] = offsetLane(end, oneWayLaneOffset(target.lanes, toLane));
  const run = Math.hypot(bx - ax, bz - az);
  const points = [], cumulative = [0];
  for (let i = 0; i <= 12; i++) {
    const t = i / 12, blend = t * t * (3 - 2 * t);
    const a = run * t * (1 - t) ** 2, b = run * t ** 2 * (t - 1);
    const point = [ax + (bx - ax) * blend + start.dx * a + end.dx * b, az + (bz - az) * blend + start.dz * a + end.dz * b];
    if (i) cumulative.push(cumulative.at(-1) + distance(points.at(-1), point));
    points.push(point);
  }
  return { enter, exit, points, cumulative, length: cumulative.at(-1) };
}

function configureForwardMovements(edges, nodes, movements, controlled) {
  for (const via of controlled) {
    const node = nodes.get(via);
    if (!node) continue;
    node.controlledMovements = true;
    node.serialMovements = node.backward.length > 1 || node.forward.length > 1;
    for (const id of node.backward) edges.get(id).forwardMovements = Array.from({ length: edges.get(id).lanes }, () => []);
  }
  for (const { via, from, to, turn, fromLanes } of movements) {
    const source = edges.get(from), target = edges.get(to);
    if (!source?.oneway || !target?.oneway || from === to || source.to !== via || target.from !== via ||
        source.layer !== 0 || target.layer !== 0 ||
        !['left', 'right', 'through'].includes(turn) || !Array.isArray(fromLanes)) continue;
    for (const [index, fromLane] of fromLanes.entries()) {
      if (!Number.isInteger(fromLane)) continue;
      const options = source.forwardMovements[fromLane];
      if (!options || options.some(option => option.id === to)) continue;
      const targetLane = turn === 'through' ? fromLane : turn === 'right' ? target.lanes - fromLanes.length + index : index;
      const lane = Math.max(0, Math.min(target.lanes - 1, targetLane));
      options.push({ id: to, direction: 1, lane, via, turn: movementCurve(source, target, fromLane, lane) });
    }
  }
}

/**
 * Builds the traffic graph from loaded tiles: { edges, nodes, signalised }. Coordinates are world metres.
 * Mapped tunnels are excluded. A configured route stays closed while its destination is missing.
 * Optional forwardConnectors map an incoming edge ID to { id, lanes }, with destination lane indices in source lane order.
 * A reviewed tile road may provide the same mapping as forwardConnector; caller-supplied mappings take precedence.
 * Each signalApproachChains item lists forward edge IDs and the stopOffset in metres back from its terminal signal.
 * Optional forwardMovements allow only the listed turns and source lane indices at their junction nodes.
 * Authored roads replace these IDs with complete, already validated world-space sections.
 */
export function buildTrafficGraph(tiles, { forwardConnectors, signalApproachChains, forwardMovements, authoredRoads } = {}) {
  const fragments = new Map(), signalised = new Set();
  const connectors = new Map(forwardConnectors);
  const controlled = forwardMovements && new Set(forwardMovements.map(({ via }) => via));
  for (const tile of tiles) {
    for (const junction of tile.junctions ?? []) if (junction.signalised) signalised.add(junction.nodeId);
    for (const road of tile.roads ?? []) {
      if (authoredRoads?.has(road.id) || (road.tunnel && !road.passageRoof) || road.geometry.length < 2) continue;
      const shifted = road.geometry.map(([x, z]) => [x + tile.x * 250, z + tile.z * 250]);
      const entry = fragments.get(road.id) ?? { road, pieces: [] };
      entry.pieces.push({ points: shifted, start: road.edgeStart ?? 0 });
      fragments.set(road.id, entry);
    }
  }
  const edges = new Map(), nodes = new Map();
  const node = id => nodes.get(id) ?? nodes.set(id, { id, forward: [], backward: [], signalised: signalised.has(id) }).get(id);
  function register(road, points, start, complete, sections) {
    if ((controlled?.has(road.from) || controlled?.has(road.to)) && !PUBLIC_ACCESS.has(road.access)) return;
    const { id } = road;
    const length = polylineLength(points);
    const retainShortTraffic = road.retainShortTraffic === true && road.oneway && complete;
    if (!(length > 0) || (length < 4 && !retainShortTraffic)) return;
    const edge = {
      id, from: road.from, to: road.to, oneway: road.oneway, lanes: Math.max(1, road.lanes ?? 2), speed: (road.maxspeed ?? 50) / 3.6,
      points, length, width: road.width ?? Math.max(3.4, (road.lanes ?? 2) * LANE), name: road.name, class: road.class,
      complete,
      // A raised bridge: its deck height follows bridgeHeight() along the whole edge (see bridges.js).
      raised: isBridge(road), layer: road.passageRoof ? 0 : road.layer ?? 0, bridgeStart: start, bridgeLength: road.edgeLength ?? length,
    };
    // Cumulative distance of each point, for sampling.
    edge.cumulative = [0];
    for (let i = 1; i < points.length; i++) edge.cumulative.push(edge.cumulative[i - 1] + distance(points[i - 1], points[i]));
    if (road.leftBusLane) edge.leftBusLane = true;
    if (retainShortTraffic) edge.retainShortTraffic = true;
    if (sections) edge.sections = sections;
    if (road.forwardConnector && !connectors.has(id)) connectors.set(id, road.forwardConnector);
    edges.set(id, edge);
    node(road.from).forward.push(id);
    node(road.to).backward.push(id);
  }
  for (const { road, pieces } of fragments.values()) {
    const { points, start } = chain(pieces);
    register(road, points, start, pieces.length === 1);
  }
  for (const { road, sections } of authoredRoads?.values() ?? []) {
    register(road, sections.map(({ x, z }) => [x, z]), 0, true, sections);
  }
  if (connectors.size) configureForwardConnectors(edges, nodes, connectors);
  if (signalApproachChains) configureSignalApproachChains(edges, nodes, signalised, signalApproachChains);
  if (controlled) configureForwardMovements(edges, nodes, forwardMovements, controlled);
  return { edges, nodes, signalised };
}

/** Deck height of a vehicle at distance s of its travel along an edge (0 on the ground), for direction +1 or -1. */
export function heightOnEdge(edge, s, direction = 1) {
  if (edge.sections) return sampleEdge(edge, s, direction).y;
  if (!edge.raised) return 0;
  const along = direction > 0 ? s : edge.length - s;
  return bridgeHeight(edge.layer, edge.bridgeStart + Math.max(0, Math.min(edge.length, along)), edge.bridgeLength);
}

/** Position and unit direction at distance s along an edge (clamped), for travel in the given direction (+1 or -1). */
export function sampleEdge(edge, s, direction = 1) {
  const along = direction > 0 ? s : edge.length - s;
  const clamped = Math.max(0, Math.min(edge.length, along));
  let i = 1;
  while (i < edge.cumulative.length - 1 && edge.cumulative[i] < clamped) i++;
  const a = edge.points[i - 1], b = edge.points[i], span = edge.cumulative[i] - edge.cumulative[i - 1] || 1;
  const k = (clamped - edge.cumulative[i - 1]) / span;
  let dx = (b[0] - a[0]) / span, dz = (b[1] - a[1]) / span;
  if (direction < 0) { dx = -dx; dz = -dz; }
  const at = { x: a[0] + (b[0] - a[0]) * k, z: a[1] + (b[1] - a[1]) * k, dx, dz };
  if (edge.sections) {
    const before = edge.sections[i - 1], after = edge.sections[i];
    const sign = direction > 0 ? 1 : -1;
    at.y = before.y + (after.y - before.y) * k;
    at.rx = sign * (before.rx + (after.rx - before.rx) * k);
    at.rz = sign * (before.rz + (after.rz - before.rz) * k);
  }
  return at;
}

/** Which of the two signal phases (0 or 1) an approach belongs to, from its direction: roughly north-south or east-west. */
export const phaseOf = (dx, dz) => (Math.abs(dx) > Math.abs(dz) ? 0 : 1);

/** Signal state for a phase at time t: "green", "amber" or "red". Phase 1 follows phase 0. */
export function signalState(phase, time) {
  const half = SIGNAL_CYCLE / 2, local = (time + (phase ? half : 0)) % SIGNAL_CYCLE;
  if (local < SIGNAL.green) return "green";
  if (local < SIGNAL.green + SIGNAL.amber) return "amber";
  return "red";
}

function pickType(random) {
  const total = VEHICLE_TYPES.reduce((sum, type) => sum + type.weight, 0);
  let roll = random() * total;
  for (const type of VEHICLE_TYPES) { roll -= type.weight; if (roll <= 0) return type; }
  return VEHICLE_TYPES[0];
}

export function createRandom(seed = 12345) {
  return () => (seed = (seed * 1664525 + 1013904223) >>> 0) / 4294967296;
}

/**
 * The simulation. `graph` can be replaced as tiles stream in (setGraph). Vehicles: { id, type, edge, direction, s, lane, speed }.
 * A vehicle's world pose comes from pose(vehicle).
 */
export function createTraffic({ graph, random = createRandom(), maxVehicles = 40, spawnRadius = 320, despawnRadius = 480 } = {}) {
  let current = graph;
  const vehicles = [];
  const reservations = new Map();
  let nextId = 1, time = 0;

  const lanesOf = (edge, direction) => (edge.oneway ? edge.lanes : Math.max(1, Math.floor(edge.lanes / 2)));
  const usable = (edge, direction) => direction > 0 || !edge.oneway;

  /** Left-hand traffic: the lane offset is to the left of travel; lane 0 is the one nearest the kerb. */
  function laneOffset(edge, lane) {
    if (edge.oneway) return oneWayLaneOffset(edge.lanes, lane); // lane 0 leftmost
    return (lane + 0.5) * LANE; // two-way: left half of the carriageway, from the centre line outwards
  }

  function pose(vehicle) {
    if (vehicle.movement) {
      const at = sampleEdge(vehicle.movement.turn, vehicle.turnS);
      return { ...at, y: 0, heading: Math.atan2(at.dx, at.dz) };
    }
    const edge = current.edges.get(vehicle.edge);
    if (!edge) return null;
    const at = sampleEdge(edge, vehicle.s, vehicle.direction);
    const offset = laneOffset(edge, vehicle.lane);
    const [x, z] = offsetLane(at, offset);
    return { x, y: at.y ?? heightOnEdge(edge, vehicle.s, vehicle.direction), z, heading: Math.atan2(at.dx, at.dz), dx: at.dx, dz: at.dz };
  }

  function spawn(near) {
    if (!current || vehicles.length >= maxVehicles) return null;
    const candidates = [...current.edges.values()].filter(edge => edge.length > 25 && edge.class !== "service" && edge.class !== "footway");
    if (!candidates.length) return null;
    for (let attempt = 0; attempt < 12; attempt++) {
      const edge = candidates[Math.floor(random() * candidates.length)];
      const direction = edge.oneway ? 1 : random() < 0.5 ? 1 : -1;
      const s = random() * edge.length;
      if (direction > 0 && s < SPAWN_CLEARANCE && current.nodes.get(edge.from)?.serialMovements) continue;
      if (direction > 0 && edge.forwardSignal && s > edge.forwardSignal.toLine &&
          (current.nodes.get(signalDestination(edge))?.serialMovements || signalState(edge.forwardSignal.approach.phase, time) !== "green")) continue;
      const at = sampleEdge(edge, s, direction);
      const d = Math.hypot(at.x - near.x, at.z - near.z);
      if (d < 70 || d > spawnRadius) continue; // not on top of the player, not beyond what is shown
      const lane = Math.floor(random() * lanesOf(edge, direction));
      if (direction > 0 && edge.forwardMovements && !edge.forwardMovements[lane]?.length) continue;
      const type = pickType(random);
      if (lane < firstAllowedLane(edge, type)) continue;
      // Do not spawn inside another vehicle.
      if (vehicles.some(other => other.edge === edge.id && other.direction === direction && other.lane === lane && Math.abs(other.s - s) < 14)) continue;
      const vehicle = { id: nextId++, type, edge: edge.id, direction, s, lane, speed: Math.min(edge.speed * 0.8, 12), wait: 0 };
      vehicles.push(vehicle);
      return vehicle;
    }
    return null;
  }

  function firstAllowedLane(edge, type) {
    return edge.leftBusLane && type.id !== "bus" && type.id !== "school-bus" ? 1 : 0;
  }

  function travelLane(edge, direction, lane, type) {
    return Math.max(firstAllowedLane(edge, type), Math.min(lane, lanesOf(edge, direction) - 1));
  }

  // Retained short edges are stitches on the reviewed one-way through route.
  function shortContinuation(edge, lane, type) {
    const node = current.nodes.get(edge.to);
    if (node?.forward.length !== 1 || !node.backward.every(id => current.edges.get(id)?.oneway)) return null;
    const ahead = current.edges.get(node.forward[0]);
    if (!ahead?.oneway || ahead.id === edge.id) return null;
    return { id: ahead.id, direction: 1, lane: travelLane(ahead, 1, lane, type) };
  }

  function nextEdge(vehicle, edge) {
    const nodeId = vehicle.direction > 0 ? edge.to : edge.from;
    const node = current.nodes.get(nodeId);
    if (!node || node.controlledMovements) return null;
    const options = [];
    for (const id of node.forward) if (id !== edge.id) options.push({ id, direction: 1 });
    for (const id of node.backward) { const other = current.edges.get(id); if (id !== edge.id && other && !other.oneway) options.push({ id, direction: -1 }); }
    const real = options.filter(option => current.edges.get(option.id)?.class !== "footway");
    if (!real.length) return null;
    return real[Math.floor(random() * real.length)];
  }

  /** Distance to the upcoming stop line on red or amber, else Infinity. */
  function signalStop(vehicle, edge) {
    if (vehicle.direction > 0 && edge.forwardSignal) {
      const { approach, toLine } = edge.forwardSignal;
      const remaining = toLine - vehicle.s;
      return remaining >= 0 && signalState(approach.phase, time) !== "green" ? remaining : Infinity;
    }
    const nodeId = vehicle.direction > 0 ? edge.to : edge.from;
    if (!current.signalised.has(nodeId)) return Infinity;
    const at = sampleEdge(edge, edge.length, vehicle.direction);
    const state = signalState(phaseOf(at.dx, at.dz), time);
    if (state === "green") return Infinity;
    const remaining = edge.length - vehicle.s - 4; // stop line 4 m before the node
    return remaining >= -1 ? remaining : Infinity; // already past the line: carry on
  }

  /** The road a vehicle will take at the end of its edge, decided once so that it can look ahead and then really go that way. */
  function chosenNext(vehicle, edge) {
    if (vehicle.direction > 0 && edge.forwardMovements) {
      const options = edge.forwardMovements[vehicle.lane];
      if (!options?.length) return null;
      if (options.length === 1) return options[0];
      const key = `movement:${edge.id}:${vehicle.lane}`;
      const previous = vehicle.nextFor === key && options.find(option => option.id === vehicle.next?.id);
      if (previous) return previous;
      vehicle.nextFor = key;
      vehicle.next = options[Math.floor(random() * options.length)];
      return vehicle.next;
    }
    if (vehicle.direction > 0 && edge.forwardConnector !== undefined) {
      const connector = edge.forwardConnector;
      const lane = connector?.lanes[vehicle.lane];
      return lane === undefined ? null : { id: connector.id, direction: 1, lane };
    }
    if (vehicle.direction > 0 && edge.retainShortTraffic) return shortContinuation(edge, vehicle.lane, vehicle.type);
    if (vehicle.nextFor !== edge.id + ":" + vehicle.direction) { vehicle.next = nextEdge(vehicle, edge); vehicle.nextFor = edge.id + ":" + vehicle.direction; }
    const option = vehicle.next;
    const ahead = option && current.edges.get(option.id);
    return ahead ? { ...option, lane: travelLane(ahead, option.direction, vehicle.lane, vehicle.type) } : null;
  }

  // Unsignalised junctions: a vehicle gives way to one on another road that is already in the junction or reaches it first.
  // The rule is stateless (no locks, so no deadlock cycles) and a vehicle that has waited too long goes anyway.
  const ZONE = 26, GIVE_UP = 6; // metres from the junction where giving way is decided; seconds of waiting before going anyway
  /** How far the vehicle is from a node: positive before reaching it (along its edge), negative after leaving it, else Infinity. */
  function distanceToNode(vehicle, nodeId) {
    const edge = current.edges.get(vehicle.edge);
    if (!edge) return Infinity;
    const endNode = vehicle.direction > 0 ? edge.to : edge.from, startNode = vehicle.direction > 0 ? edge.from : edge.to;
    if (endNode === nodeId) return edge.length - vehicle.s;
    if (startNode === nodeId) return -vehicle.s;
    return Infinity;
  }
  const arms = node => node.forward.length + node.backward.length;

  function signalDestination(edge) {
    return current.edges.get(edge.forwardSignal?.approach.terminal)?.to;
  }

  function junctionGate(vehicle, edge, option) {
    if (vehicle.direction < 0) return null;
    const signal = signalDestination(edge);
    const via = option?.via ?? signal;
    if (!current.nodes.get(via)?.serialMovements) return null;
    const line = signal === via ? edge.forwardSignal.toLine : -1;
    const beforeBlend = option ? option.turn.enter - vehicle.type.length / 2 - 1 : vehicle.s;
    let phase = signal === via ? edge.forwardSignal.approach.phase : undefined;
    if (phase === undefined && current.signalised.has(via)) {
      const at = sampleEdge(edge, edge.length);
      phase = phaseOf(at.dx, at.dz);
    }
    return { via, phase, distance: Math.max(0, (line >= vehicle.s ? line : beforeBlend) - vehicle.s) };
  }

  function clearReservations() {
    for (const [via, owner] of reservations) {
      const road = current.edges.get(owner.edge);
      const approaching = road && (road.to === via || signalDestination(road) === via);
      const clearing = road?.from === via && owner.s <= clearingDistance(owner.type.length);
      if (!vehicles.includes(owner) || !(owner.movement?.via === via || approaching || clearing)) reservations.delete(via);
    }
  }

  /** Distance to the stop line when the vehicle must give way at the end of its edge, else Infinity. */
  function giveWayStop(vehicle, edge) {
    const nodeId = vehicle.direction > 0 ? edge.to : edge.from;
    const node = current.nodes.get(nodeId);
    if (!node || node.controlledMovements || node.laneDisjointMerge || current.signalised.has(nodeId) || arms(node) < 3 || vehicle.wait > GIVE_UP) return Infinity;
    const remaining = edge.length - vehicle.s;
    if (remaining > ZONE || remaining < 1) return Infinity; // too far to matter, or already past the line
    for (const other of vehicles) {
      if (other === vehicle || other.edge === vehicle.edge) continue;
      const d = distanceToNode(other, nodeId);
      if (d > ZONE || d < -(other.type.length + 4)) continue;
      // Already in the junction, or nearer to it (the lower id wins a tie): the other goes first.
      if (d <= 0 || d < remaining || (d === remaining && other.id < vehicle.id)) return Math.max(0, remaining - 4);
    }
    return Infinity;
  }

  function leaderGap(vehicle, edge) {
    let best = Infinity;
    for (const other of vehicles) {
      if (other === vehicle || other.edge !== vehicle.edge || other.direction !== vehicle.direction || other.lane !== vehicle.lane) continue;
      if (other.s <= vehicle.s) continue; // behind, or level: not a leader
      const gap = other.s - vehicle.s - (other.type.length + vehicle.type.length) / 2;
      if (gap < best) best = gap;
    }
    let crossesShortLink = Boolean(edge.retainShortTraffic);
    let shortGap = crossesShortLink ? best : Infinity;
    // Near the end of the edge, a vehicle at the start of the road ahead is the leader too.
    if ((best === Infinity || edge.forwardConnector || edge.forwardMovements) && edge.length - vehicle.s < 40) {
      let option = chosenNext(vehicle, edge);
      let routeDistance = option?.turn ? option.turn.enter - vehicle.s + option.turn.length - option.turn.exit : edge.length - vehicle.s;
      while (option) {
        const ahead = current.edges.get(option.id);
        crossesShortLink ||= Boolean(ahead.retainShortTraffic);
        for (const other of vehicles) {
          if (other === vehicle || other.edge !== option.id || other.direction !== option.direction || other.lane !== option.lane) continue;
          const gap = routeDistance + other.s - (other.type.length + vehicle.type.length) / 2;
          if (gap < best) best = gap;
          if (crossesShortLink && gap < shortGap) shortGap = gap;
        }
        if (!ahead.retainShortTraffic || option.direction < 0) break;
        routeDistance += ahead.length;
        if (routeDistance >= 40) break;
        option = shortContinuation(ahead, option.lane, vehicle.type);
      }
    }
    return { best, shortStop: Math.max(0, shortGap - 2) };
  }

  /** Distance to the nearest obstacle (a pedestrian, say) in the path of a vehicle, else Infinity. */
  function obstacleGap(vehicle, here, obstacles) {
    let best = Infinity, vehicleStop = Infinity;
    for (const obstacle of obstacles) {
      if (Number.isFinite(obstacle.y) && Math.abs(obstacle.y - here.y) > 2) continue;
      const ox = obstacle.x - here.x, oz = obstacle.z - here.z;
      const ahead = ox * here.dx + oz * here.dz, side = Math.abs(ox * here.dz - oz * here.dx);
      const driver = Number.isFinite(obstacle.halfLength) && obstacle.halfLength > 0;
      if (ahead <= 0 || ahead >= (driver ? 45 : 22) || side >= 1.9) continue;
      const gap = ahead - vehicle.type.length / 2 - (driver ? obstacle.halfLength + 1 : 1.5);
      best = Math.min(best, gap);
      if (driver) vehicleStop = Math.min(vehicleStop, Math.max(0, gap));
    }
    return { best, vehicleStop };
  }

  function finishMovement(vehicle) {
    const move = vehicle.movement;
    if (vehicle.turnS < move.turn.length) return;
    vehicle.edge = move.id;
    vehicle.s = move.turn.exit + vehicle.turnS - move.turn.length;
    vehicle.lane = move.lane;
    vehicle.movement = null;
  }

  function turnGap(vehicle) {
    const move = vehicle.movement;
    let gap = Infinity;
    for (const other of vehicles) {
      const clearance = (vehicle.type.length + other.type.length) / 2 + 2;
      if (other !== vehicle && other.edge === move.id && other.direction === 1 && other.lane === move.lane) {
        gap = Math.min(gap, move.turn.length - vehicle.turnS + other.s - move.turn.exit - clearance);
      }
      if (other !== vehicle && other.movement === move && other.turnS > vehicle.turnS) {
        gap = Math.min(gap, other.turnS - vehicle.turnS - clearance);
      }
    }
    return gap;
  }

  function update(dt, near, obstacles = []) {
    time += dt;
    if (!current) return;
    clearReservations();
    for (let i = vehicles.length - 1; i >= 0; i--) {
      const vehicle = vehicles[i], edge = current.edges.get(vehicle.edge);
      if (!edge) { vehicles.splice(i, 1); continue; }
      const here = pose(vehicle);
      if (here && Math.hypot(here.x - near.x, here.z - near.z) > despawnRadius) { vehicles.splice(i, 1); continue; }
      // A vehicle stuck for a long time out of the player's sight is removed (a gridlock breaker); new ones spawn elsewhere.
      if (here && vehicle.wait > STUCK_SECONDS && Math.hypot(here.x - near.x, here.z - near.z) > 70) { vehicles.splice(i, 1); continue; }
      // Desired speed: the speed limit (a little under it), slower for long vehicles, cut by the gap to the leader and signals.
      let desired = Math.min(edge.speed * 0.85, vehicle.type.length > 7 ? 11 : 15);
      const move = !vehicle.movement && vehicle.direction > 0 && edge.forwardMovements ? chosenNext(vehicle, edge) : null;
      const connectorStop = !vehicle.movement && vehicle.direction > 0 && (edge.forwardConnector === null || edge.forwardMovements && !move)
        ? Math.max(0, edge.length - vehicle.s - vehicle.type.length / 2 - 1) : Infinity;
      const gate = !vehicle.movement && junctionGate(vehicle, edge, move);
      const holder = gate && reservations.get(gate.via);
      const redGate = gate?.phase !== undefined && signalState(gate.phase, time) !== 'green';
      const reservationStop = gate && holder !== vehicle && (holder || redGate) ? gate.distance : Infinity;
      const stopAtSignal = vehicle.movement ? Infinity : signalStop(vehicle, edge);
      if (vehicle.movement && !current.edges.has(vehicle.movement.id)) { vehicles.splice(i, 1); continue; }
      if (vehicle.movement || (move && move.turn.enter - vehicle.s < 12)) desired = Math.min(desired, 6);
      const obstacle = here && obstacles.length ? obstacleGap(vehicle, here, obstacles) : null;
      const leader = vehicle.movement ? null : leaderGap(vehicle, edge);
      const stop = Math.min(connectorStop, reservationStop, stopAtSignal, vehicle.movement ? turnGap(vehicle) : giveWayStop(vehicle, edge),
        (leader?.best ?? Infinity) - 2, obstacle?.best ?? Infinity);
      if (stop < 60) desired = Math.min(desired, Math.max(0, Math.sqrt(2 * 3.5 * Math.max(0, stop))));
      const rate = desired > vehicle.speed ? 2.2 : 5.5; // m/s^2: gentle acceleration, firmer braking
      vehicle.wait = vehicle.speed < 0.3 ? (vehicle.wait ?? 0) + dt : 0;
      vehicle.speed += Math.sign(desired - vehicle.speed) * Math.min(Math.abs(desired - vehicle.speed), rate * dt);
      const enforcedStop = Math.min(connectorStop, reservationStop, obstacle?.vehicleStop ?? Infinity,
        vehicle.direction > 0 && edge.forwardSignal ? stopAtSignal : Infinity);
      const advance = Math.min(vehicle.speed * dt, leader?.shortStop ?? Infinity);
      if (advance < vehicle.speed * dt) vehicle.speed = 0;
      if (advance >= enforcedStop) {
        if (vehicle.movement) {
          vehicle.turnS += enforcedStop;
          finishMovement(vehicle);
        } else vehicle.s += enforcedStop;
        vehicle.speed = 0;
        continue;
      }
      if (gate && advance > 0 && advance >= gate.distance) reservations.set(gate.via, vehicle);
      if (vehicle.movement) {
        vehicle.turnS += advance;
        finishMovement(vehicle);
        continue;
      }
      vehicle.s += advance;
      if (move && vehicle.s >= move.turn.enter) {
        vehicle.movement = move;
        vehicle.turnS = vehicle.s - move.turn.enter;
        vehicle.s = move.turn.enter;
        finishMovement(vehicle);
        continue;
      }
      let crossed = edge;
      while (vehicle.s >= crossed.length) {
        const option = chosenNext(vehicle, crossed);
        if (!option) { vehicles.splice(i, 1); break; }
        const nextEdgeData = current.edges.get(option.id);
        vehicle.s = Math.max(0, vehicle.s - crossed.length);
        vehicle.edge = option.id;
        vehicle.direction = option.direction;
        vehicle.lane = option.lane;
        if (!usable(nextEdgeData, option.direction)) { vehicles.splice(i, 1); break; }
        if (!nextEdgeData.retainShortTraffic) break;
        crossed = nextEdgeData;
      }
    }
    while (vehicles.length < maxVehicles && spawn(near)) { /* fill up to the limit */ }
  }

  return {
    vehicles, pose, maxVehicles,
    get time() { return time; },
    setGraph(graph) { current = graph; },
    update, spawn,
    signalState: (dx, dz) => signalState(phaseOf(dx, dz), time),
  };
}

import { projectOsm } from './project.js';
import { convexHull, distinctPoints, offsetPolyline, simplifyPolyline } from './geometry.js';

export { offsetPolyline, simplifyPolyline } from './geometry.js';

export const LANE_WIDTH = 3.4;

// [two-way lanes, one-way lanes, speed in km/h]. One-lane service roads can share a lane.
const ROAD_DEFAULTS = {
  motorway: [4, 3, 90],
  motorway_link: [2, 1, 50],
  trunk: [4, 2, 70],
  trunk_link: [2, 1, 50],
  primary: [4, 2, 50],
  primary_link: [2, 1, 50],
  secondary: [2, 2, 50],
  secondary_link: [2, 1, 50],
  tertiary: [2, 1, 50],
  tertiary_link: [2, 1, 50],
  residential: [2, 1, 40],
  unclassified: [2, 1, 40],
  living_street: [1, 1, 20],
  service: [1, 1, 20],
  track: [1, 1, 20],
  road: [2, 1, 40],
  raceway: [2, 2, 50],
};
const WALK_CLASSES = new Set(['footway', 'pedestrian', 'steps', 'path', 'corridor', 'crossing']);

const hasValue = (value, part) => value?.split(';').some(token => token.trim() === part) ?? false;
const enabled = value => Boolean(value && value !== 'no' && value !== '0');
const laneCount = value => /^\d+$/.test(value ?? '') && Number(value) <= 64 ? Number(value) : 0;

function parseSpeed(value, fallback) {
  const match = /^(\d+(?:\.\d+)?)\s*(km\/h|kph|mph)?$/i.exec(value?.trim() ?? '');
  return match && Number(match[1]) > 0
    ? Math.round(Number(match[1]) * (match[2]?.toLowerCase() === 'mph' ? 1.609344 : 1))
    : fallback;
}

function roadAttributes(tags) {
  const roadClass = tags.highway;
  const [twoWayLanes, oneWayLanes, speed] = ROAD_DEFAULTS[roadClass];
  const implicitOneway = roadClass === 'motorway' || tags.junction === 'roundabout';
  const oneway = tags.oneway === '-1' || ['yes', 'true', '1'].includes(tags.oneway)
    || (tags.oneway == null && implicitOneway);
  const lanes = laneCount(tags.lanes) || (oneway ? oneWayLanes : twoWayLanes);
  const bridge = enabled(tags.bridge);
  const tunnel = enabled(tags.tunnel);
  return {
    class: roadClass,
    name: tags.name ?? null,
    lanes,
    oneway,
    maxspeed: parseSpeed(tags.maxspeed, speed),
    bridge,
    tunnel,
    layer: tags.layer != null && Number.isFinite(Number(tags.layer))
      ? Number(tags.layer)
      : Number(bridge) - Number(tunnel),
    access: tags.motorcar ?? tags.motor_vehicle ?? tags.vehicle ?? tags.access ?? null,
  };
}

export function buildLaneCenterlines(points, road, tags = {}) {
  const { lanes, oneway } = road;
  const lines = [];
  function add(direction, count, firstOffset, spacing = LANE_WIDTH) {
    const geometry = direction === 'backward' ? points.slice().reverse() : points;
    for (let index = 0; index < count; index++) {
      lines.push({
        direction,
        index,
        points: offsetPolyline(geometry, firstOffset + index * spacing),
      });
    }
  }

  if (oneway) {
    add('forward', lanes, (lanes - 1) * LANE_WIDTH / 2, -LANE_WIDTH);
  } else if (lanes === 1) {
    add('forward', 1, 0);
    add('backward', 1, 0);
  } else {
    const markedCenter = Math.min(laneCount(tags['lanes:both_ways']), lanes - 2);
    const declaredForward = laneCount(tags['lanes:forward']);
    const declaredBackward = laneCount(tags['lanes:backward']);
    const center = markedCenter;
    const through = lanes - center;
    const estimate = declaredForward || (declaredBackward ? through - declaredBackward : Math.ceil(through / 2));
    const forward = Math.max(1, Math.min(through - 1, estimate));
    const split = (through - 2 * forward) * LANE_WIDTH / 2;
    const firstOffset = (center + 1) * LANE_WIDTH / 2;
    add('forward', forward, firstOffset + split);
    add('backward', through - forward, firstOffset - split);
    add('both', center, split - (center - 1) * LANE_WIDTH / 2);
  }
  return lines;
}

function isWalkWay(tags) {
  return WALK_CLASSES.has(tags.highway);
}

function isRoadWay(tags) {
  const access = tags.motorcar ?? tags.motor_vehicle ?? tags.vehicle ?? tags.access;
  return Object.hasOwn(ROAD_DEFAULTS, tags.highway) && access !== 'no' && tags.area !== 'yes';
}

function readWays(elements) {
  const pointsById = new Map(elements.filter(element => element.type === 'node').map(node => [node.id, node]));
  const ways = [];
  for (const way of elements) {
    const tags = way.tags ?? {};
    if (way.type !== 'way' || (!isRoadWay(tags) && !isWalkWay(tags))) continue;
    const ids = way.nodes ?? [];
    const positions = ids.map((id, index) => pointsById.get(id) ?? way.geometry?.[index]);
    let start = 0;
    for (let i = 0; i <= ids.length; i++) {
      if (Number.isFinite(positions[i]?.lon) && Number.isFinite(positions[i]?.lat)) continue;
      if (i - start >= 2) {
        ways.push({
          id: way.id,
          start,
          ids: ids.slice(start, i),
          points: positions.slice(start, i).map(projectOsm),
          tags,
        });
      }
      start = i + 1;
    }
  }
  return ways;
}

function buildLayer(ways, special, drivable) {
  const nodes = new Map();
  const uses = new Map();
  const edges = [];
  for (const way of ways) {
    for (const id of way.ids) uses.set(id, (uses.get(id) ?? 0) + 1);
  }

  function addNode(id, point, edgeId) {
    if (!nodes.has(id)) nodes.set(id, { id, point, signalised: false, crossing: false, ...special.get(id), edges: [] });
    nodes.get(id).edges.push(edgeId);
  }

  for (const way of ways) {
    const { ids, tags } = way;
    const attributes = drivable ? roadAttributes(tags) : {
      class: tags.footway === 'crossing' ? 'crossing' : tags.highway,
      name: tags.name ?? null,
    };
    let start = 0;
    for (let end = 1; end < ids.length; end++) {
      const id = ids[end];
      if (end < ids.length - 1 && uses.get(id) === 1 && !special.has(id)) continue;
      const edgeId = `${way.id}:${way.start + start}`;
      const raw = distinctPoints(way.points.slice(start, end + 1));
      let points = distinctPoints(simplifyPolyline(raw));
      if (points.length < 2 && raw.length > 2) points = raw;
      const reversed = drivable && tags.oneway === '-1';
      const from = reversed ? id : ids[start];
      const to = reversed ? ids[start] : id;
      start = end;
      if (points.length < 2) continue;
      if (reversed) points.reverse();
      const edge = { id: edgeId, wayId: way.id, from, to, ...attributes, points };
      if (drivable) {
        edge.width = edge.lanes * LANE_WIDTH;
        edge.laneCenterlines = buildLaneCenterlines(points, edge, tags);
      }
      edges.push(edge);
      addNode(from, points[0], edgeId);
      addNode(to, points.at(-1), edgeId);
    }
  }
  return { nodes: [...nodes.values()], edges };
}

export const junctionArmDepth = (width, segmentLength) => Math.min(width / 2, segmentLength * 0.45);

function buildJunctions(nodes, edges) {
  const byId = new Map(edges.map(edge => [edge.id, edge]));
  return nodes.flatMap(node => {
    if (node.edges.length < 3 && !node.signalised && !node.crossing) return [];
    const corners = [node.point];
    const used = new Set();
    for (const id of node.edges) {
      if (used.has(id)) continue;
      used.add(id);
      const edge = byId.get(id);
      const neighbours = [];
      if (edge.from === node.id) neighbours.push(edge.points[1]);
      if (edge.to === node.id) neighbours.push(edge.points.at(-2));
      for (const [x, z] of neighbours) {
        const dx = x - node.point[0];
        const dz = z - node.point[1];
        const length = Math.hypot(dx, dz);
        if (!length) continue;
        const halfWidth = edge.width / 2;
        const depth = junctionArmDepth(edge.width, length);
        const mouth = [node.point[0] + dx / length * depth, node.point[1] + dz / length * depth];
        const left = [dz / length * halfWidth, -dx / length * halfWidth];
        corners.push([mouth[0] + left[0], mouth[1] + left[1]], [mouth[0] - left[0], mouth[1] - left[1]]);
      }
    }
    const polygon = convexHull(corners);
    return [{ nodeId: node.id, point: node.point, signalised: node.signalised, crossing: node.crossing,
      polygon: polygon.length >= 3 ? [...polygon, polygon[0]] : [] }];
  });
}

/**
 * Build two independent graphs from Overpass out geom. OSM node IDs define connectivity:
 * coincident or intersecting lines without a shared node may be grade-separated.
 * Geometry follows each edge from its source to its destination, reversing OSM oneway=-1.
 */
export function buildRoadGraph(input) {
  const elements = (Array.isArray(input) ? input : input.elements).slice().sort((a, b) => a.id - b.id);
  const taggedNodes = new Map();
  const crossings = new Map();
  for (const node of elements) {
    if (node.type !== 'node') continue;
    const tags = node.tags ?? {};
    const signalised = hasValue(tags.highway, 'traffic_signals');
    const crossing = hasValue(tags.highway, 'crossing');
    if (!signalised && !crossing) continue;
    taggedNodes.set(node.id, { signalised, crossing });
    if (crossing && Number.isFinite(node.lon) && Number.isFinite(node.lat)) {
      crossings.set(node.id, { id: node.id, point: projectOsm(node), signalised });
    }
  }

  const ways = readWays(elements);
  const walkWays = ways.filter(way => isWalkWay(way.tags));
  const roadWays = ways.filter(way => isRoadWay(way.tags));
  const roadIds = new Set(roadWays.flatMap(way => way.ids));
  for (const way of walkWays) {
    if (way.tags.footway !== 'crossing' && way.tags.highway !== 'crossing') continue;
    for (const id of way.ids) {
      if (roadIds.has(id)) taggedNodes.set(id, { signalised: taggedNodes.get(id)?.signalised ?? false, crossing: true });
    }
  }

  const graph = buildLayer(roadWays, taggedNodes, true);
  graph.junctions = buildJunctions(graph.nodes, graph.edges);
  graph.pedestrian = { ...buildLayer(walkWays, taggedNodes, false), crossings: [...crossings.values()] };
  return graph;
}

import { createTunnelGeometry, pointOffset, roadStrip, terrainSurfaceFromHole } from "../tunnel-prototype/geometry.js";
import { createFortCanningMergeAlignment } from "./merge-alignment.js";
import { mergeWalkways } from "./walkways.js";

const TERRAIN_MARGIN = 40;
const JOIN_TOLERANCE = .002;

function sharedPoint(section, offset, join) {
  const point = pointOffset(section, offset);
  if (Math.hypot(...point.map((axis, index) => axis - join[index])) > JOIN_TOLERANCE) {
    throw new Error("The Fort Canning road edges disagree at the common section");
  }
  return join;
}

function ribbon(rows, left, right, joint, leftJoin, rightJoin) {
  return rows.map(row => row === joint
    ? { left: sharedPoint(row, left, leftJoin), right: sharedPoint(row, right, rightJoin) }
    : { left: pointOffset(row, left), right: pointOffset(row, right) });
}

function weldRoads(ribbons) {
  const position = [], indices = [], byPoint = new Map();
  for (const rows of ribbons) {
    const surface = roadStrip("road", rows, row => row.left, row => row.right);
    const remap = [];
    for (let i = 0; i < surface.position.length; i += 3) {
      const point = surface.position.subarray(i, i + 3);
      const key = point.join(",");
      if (!byPoint.has(key)) {
        byPoint.set(key, position.length / 3);
        position.push(...point);
      }
      remap.push(byPoint.get(key));
    }
    for (const index of surface.indices) indices.push(remap[index]);
  }
  return { id: "road", position: new Float32Array(position), indices: new Uint32Array(indices) };
}

function cutTerrain(link, penang, downstreamLeft, downstreamRight) {
  // Follow the outer edge of the joined carriageways, including the gap between the two feeders.
  const boundary = [
    ...link.map(row => row.left),
    ...downstreamLeft.slice(1).map(row => row.left),
    ...downstreamRight.toReversed().map(row => row.right),
    ...penang.toReversed().slice(1).map(row => row.right),
    ...penang.map(row => row.left),
    ...link.toReversed().slice(1).map(row => row.right),
  ].map(([x, , z]) => [x, z]);
  const x = boundary.map(point => point[0]), z = boundary.map(point => point[1]);
  const bounds = {
    minX: Math.fround(Math.min(...x) - TERRAIN_MARGIN), maxX: Math.fround(Math.max(...x) + TERRAIN_MARGIN),
    minZ: Math.fround(Math.min(...z) - TERRAIN_MARGIN), maxZ: Math.fround(Math.max(...z) + TERRAIN_MARGIN),
  };
  return { bounds, terrain: terrainSurfaceFromHole(bounds, boundary) };
}

function lanePath(branch, offset, downstream, onwardOffset, joint) {
  const branchPoints = branch.map(row => pointOffset(row, offset));
  sharedPoint(branch.at(-1), offset, joint);
  sharedPoint(downstream[0], onwardOffset, joint);
  branchPoints[branchPoints.length - 1] = joint;
  const points = [...branchPoints, ...downstream.slice(1).map(row => pointOffset(row, onwardOffset))];
  let s = 0;
  const path = points.map(([x, y, z], index) => {
    if (index) s += Math.hypot(x - points[index - 1][0], z - points[index - 1][2]);
    return { x, y, z, s };
  });
  return { path, seamS: path[branch.length - 1].s };
}

/** Three Link lanes and two level Penang lanes join a welded five-lane surface. */
export function createFortCanningMergeGeometry(profile) {
  const alignment = createFortCanningMergeAlignment(profile);
  const { link, penang, downstream, widths, seam } = alignment;
  const joint = { x: seam.x, y: 0, z: seam.z, rx: -seam.tz, rz: seam.tx };
  const divider = (widths.link - widths.penang) / 2;
  const leftEdge = pointOffset(joint, -widths.downstream / 2);
  const middle = pointOffset(joint, divider);
  const rightEdge = pointOffset(joint, widths.downstream / 2);
  const linkRoad = ribbon(link, -widths.link / 2, widths.link / 2, link.at(-1), leftEdge, middle);
  const penangRoad = ribbon(penang, -widths.penang / 2, widths.penang / 2, penang.at(-1), middle, rightEdge);
  const downstreamLeft = ribbon(downstream, -widths.downstream / 2, divider, downstream[0], leftEdge, middle);
  const downstreamRight = ribbon(downstream, divider, widths.downstream / 2, downstream[0], middle, rightEdge);
  const road = weldRoads([linkRoad, penangRoad, downstreamLeft, downstreamRight]);
  const { bounds, terrain } = cutTerrain(linkRoad, penangRoad, downstreamLeft, downstreamRight);
  const tunnel = createTunnelGeometry(alignment.profile, { sections: link, includeTerrain: false });
  const halfLane = profile.laneWidth / 2;
  const linkLane = lanePath(link, widths.link / 2 - halfLane, downstream, divider - halfLane, pointOffset(joint, divider - halfLane));
  const penangLane = lanePath(penang, -widths.penang / 2 + halfLane, downstream, divider + halfLane, pointOffset(joint, divider + halfLane));
  return {
    alignment, bounds,
    surfaces: [road, terrain, ...tunnel.surfaces.filter(surface => surface.id !== "road"), ...mergeWalkways(profile)],
    lanes: { link: linkLane.path, penang: penangLane.path },
    seam: { ...seam, y: 0, stations: { link: linkLane.seamS, penang: penangLane.seamS } },
    coveredFrom: tunnel.coveredFrom, coveredTo: tunnel.coveredTo, clearance: tunnel.clearance,
  };
}

const PENANG_FEEDER = "654224115:0";

function sectionsBetween(points, { start, end, edgeId }) {
  const sections = points.filter(({ s }) => s >= start && s <= end);
  if (sections[0]?.s !== start || sections.at(-1)?.s !== end) {
    throw new Error("Fort Canning grade is missing the endpoints of " + edgeId);
  }
  return sections;
}

/** Bind the road mesh's world-space lane frames and elevations to the matching mapped edges. */
export function fortCanningTrafficRoads(profile, alignment, tiles) {
  const mapped = new Map();
  for (const tile of tiles) {
    for (const road of tile.roads ?? []) mapped.set(road.id, road);
  }
  const authoredRoads = new Map();
  function add(id, sections, lanes, from, to) {
    const road = mapped.get(id);
    if (!road?.oneway || road.lanes !== lanes || road.from !== from || road.to !== to) {
      throw new Error("Missing matching Fort Canning road " + id);
    }
    authoredRoads.set(id, { road, sections });
  }

  const { chain, exitNodeId, exitWitness } = profile.simulation;
  for (const entry of chain) {
    add(entry.edgeId, sectionsBetween(alignment.link, entry), profile.lanes, entry.from, entry.to);
  }
  const feeder = mapped.get(PENANG_FEEDER);
  add(PENANG_FEEDER, alignment.penang, 2, feeder?.from, exitNodeId);

  const downstream = exitWitness.edges[0];
  const downstreamId = downstream.wayId + ":0";
  const road = mapped.get(downstreamId);
  if (!road?.oneway || road.from !== exitNodeId || road.to !== downstream.to || road.lanes !== downstream.lanes) {
    throw new Error("Missing matching Fort Canning continuation " + downstreamId);
  }
  const forwardConnectors = new Map([
    [chain.at(-1).edgeId, { id: downstreamId, lanes: [0, 1, 2] }],
    [PENANG_FEEDER, { id: downstreamId, lanes: [3, 4] }],
  ]);
  return { authoredRoads, forwardConnectors };
}

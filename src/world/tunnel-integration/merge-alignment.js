import { offsetPolyline } from "../network/geometry.js";

const RISE_START = 451;
const RISE_DEPTH = 4.92;
const GRADE_EASE = 10;
const TAPER_START = 493;
const LINK_JOIN_STRAIGHT = .75;
const PENANG_JOIN_STRAIGHT = 1;
const SAMPLE_STEP = .5;

const lerp = (a, b, t) => a + (b - a) * t;
const clamp01 = value => Math.max(0, Math.min(1, value));
const smoothstep = value => value * value * (3 - 2 * value);
const move = ({ x, z }, dx, dz, distance) => ({ x: x + dx * distance, z: z + dz * distance });

function direction(a, b) {
  const run = Math.hypot(b.x - a.x, b.z - a.z);
  return { tx: (b.x - a.x) / run, tz: (b.z - a.z) / run };
}

function pointAt(points, s) {
  const next = points.findIndex(point => point.s > s);
  const index = next < 0 ? points.length - 1 : next;
  const a = points[index - 1], b = points[index];
  const t = (s - a.s) / (b.s - a.s);
  return { x: lerp(a.x, b.x, t), z: lerp(a.z, b.z, t), ...direction(a, b) };
}

function easeJoin(a, b, tangentIn, tangentOut, t) {
  const run = Math.hypot(b.x - a.x, b.z - a.z);
  const f = smoothstep(t);
  const m0 = run * t * (t - 1) ** 2;
  const m1 = run * t ** 2 * (t - 1);
  return {
    x: lerp(a.x, b.x, f) + m0 * tangentIn.tx + m1 * tangentOut.tx,
    z: lerp(a.z, b.z, f) + m0 * tangentIn.tz + m1 * tangentOut.tz,
  };
}

function sampleStations(start, end, step = SAMPLE_STEP) {
  const count = Math.ceil((end - start) / step);
  return Array.from({ length: count + 1 }, (_, index) => lerp(start, end, index / count));
}

function ascent(s, plateauEnd, depth, mergeStation) {
  if (s <= RISE_START) return lerp(-depth, -RISE_DEPTH, smoothstep((s - plateauEnd) / (RISE_START - plateauEnd)));
  const run = s - RISE_START, remaining = mergeStation - s;
  const grade = RISE_DEPTH / (mergeStation - RISE_START - GRADE_EASE);
  if (run < GRADE_EASE) return -RISE_DEPTH + grade * run ** 2 / (2 * GRADE_EASE);
  if (remaining < GRADE_EASE) return -grade * remaining ** 2 / (2 * GRADE_EASE);
  return -RISE_DEPTH + grade * (run - GRADE_EASE / 2);
}

function laneFrames(points) {
  const right = offsetPolyline(points.map(({ x, z }) => [x, z]), -1);
  if (right.length !== points.length) throw new Error("Fort Canning merge alignment has an unexpected miter bevel");
  return points.map((point, index) => {
    if (point.tx !== undefined) return { ...point, rx: -point.tz, rz: point.tx };
    const [x, z] = right[index], rx = x - point.x, rz = z - point.z;
    const length = Math.hypot(rx, rz);
    return { ...point, tx: rz / length, tz: -rx / length, rx, rz };
  });
}

function densify(points) {
  let s = 0;
  return points.flatMap(([x, z], index) => {
    if (!index) return [{ x, y: 0, z, s: 0 }];
    const [px, pz] = points[index - 1], start = s;
    s += Math.hypot(x - px, z - pz);
    return sampleStations(start, s).slice(1).map(station => {
      const t = (station - start) / (s - start);
      return { x: lerp(px, x, t), y: 0, z: lerp(pz, z, t), s: station };
    });
  });
}

/** Simulated lane layout over the pinned ways. Station s on Link references the original profile. */
export function createFortCanningMergeAlignment(profile) {
  const incoming = profile.crossings.find(({ edgeId }) => edgeId === "654224115:0");
  const exitWays = profile.simulation.exitWitness.edges;
  const outgoing = exitWays.flatMap(({ points }, index) => index ? points.slice(1) : points);
  const [x, z] = outgoing[0], [nx, nz] = outgoing[1];
  const merge = { x, z };
  const exit = direction(merge, { x: nx, z: nz });
  const { tx, tz } = exit;
  const leftX = tz, leftZ = -tx;
  const widths = { link: profile.width, penang: incoming.width, downstream: exitWays[0].lanes * profile.laneWidth };
  if (Math.abs(widths.link + widths.penang - widths.downstream) > 1e-8) {
    throw new Error("Pin matching incoming and outgoing Fort Canning lane widths");
  }

  const [px, pz] = incoming.points[0], [ex, ez] = incoming.points.at(-1);
  const penangStart = { x: px, z: pz }, penangIn = direction(penangStart, { x: ex, z: ez });
  const penangEnd = move(merge, leftX, leftZ, -widths.link / 2);
  // Settle the Penang divider first so the next Link miter cannot cut into it.
  const penangTail = move(penangEnd, tx, tz, -PENANG_JOIN_STRAIGHT);
  const penangRun = Math.hypot(penangTail.x - px, penangTail.z - pz);
  const penangPoints = sampleStations(0, penangRun).map(s => {
    const { x, z } = easeJoin(penangStart, penangTail, penangIn, exit, s / penangRun);
    return [x, z];
  });
  penangPoints.push([penangEnd.x, penangEnd.z]);

  const mergeStation = profile.length, plateauEnd = mergeStation - profile.rampLength;
  const original = profile.fragments.flatMap(({ points }, index) => index ? points.slice(1) : points);
  const start = pointAt(original, TAPER_START);
  const linkEnd = move(merge, leftX, leftZ, widths.penang / 2);
  const linkTail = move(linkEnd, tx, tz, -LINK_JOIN_STRAIGHT);
  const taperEnd = mergeStation - LINK_JOIN_STRAIGHT;
  const sampleSet = new Set([
    ...original.filter(point => point.s > plateauEnd && point.s < TAPER_START).map(point => point.s),
    ...sampleStations(plateauEnd, TAPER_START),
    ...sampleStations(TAPER_START, taperEnd),
    RISE_START, RISE_START + GRADE_EASE, mergeStation - GRADE_EASE, 476, 485, 501, mergeStation,
  ]);
  const adjusted = [...sampleSet].sort((a, b) => a - b).filter((s, index, all) => !index || s - all[index - 1] > 1e-7).map(s => {
    const t = clamp01((s - TAPER_START) / (taperEnd - TAPER_START));
    const point = s === mergeStation ? linkEnd : s < TAPER_START ? pointAt(original, s) : easeJoin(start, linkTail, start, exit, t);
    // Keep the mapped side footpath outside the open cut, then separate the two approach ribbons.
    const sideShift = -.8 * smoothstep(clamp01((s - RISE_START) / 25)) * smoothstep(clamp01((501 - s) / 16));
    const bulge = .4 * 16 * t ** 2 * (1 - t) ** 2;
    return { ...move(point, leftX, leftZ, sideShift + bulge), y: ascent(s, plateauEnd, profile.depth, mergeStation), s };
  });
  Object.assign(adjusted.at(-1), exit, { y: 0 });
  const fragments = profile.fragments.map(fragment => ({ ...fragment, points: fragment.points.filter(point => point.s < plateauEnd - 1e-7) }));
  fragments.at(-1).points.push(...adjusted);
  const { clearance, roofThickness } = profile.simulation;
  const roofEnd = adjusted.findLast(({ y }) => y + clearance + roofThickness <= 0).s;
  const adapted = {
    ...profile,
    fragments,
    approaches: { ...profile.approaches, exit: [adjusted.at(-1)] },
    simulation: { ...profile.simulation, roof: { ...profile.simulation.roof, end: roofEnd } },
  };
  const linkPoints = [...adapted.approaches.entry.slice(0, -1), ...fragments.flatMap(({ points }, index) => index ? points.slice(1) : points)];
  const penangRoute = densify(penangPoints), downstreamRoute = densify(outgoing);
  Object.assign(penangRoute.at(-1), exit);
  Object.assign(downstreamRoute[0], exit);
  return {
    profile: adapted,
    link: laneFrames(linkPoints),
    penang: laneFrames(penangRoute),
    downstream: laneFrames(downstreamRoute),
    widths,
    seam: { x, z, tx, tz, divider: move(merge, leftX, leftZ, (widths.penang - widths.link) / 2) },
  };
}

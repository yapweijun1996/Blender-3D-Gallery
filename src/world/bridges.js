// Bridges and flyovers: a road tagged as a bridge (layer 1 or more) is lifted off the ground and ramps up from its ends.
// The tiles say where each fragment starts along its whole edge (edgeStart) and how long the edge is (edgeLength).
export const LAYER_HEIGHT = 5.5; // metres per OSM layer
const MAX_GRADE = 0.08;          // the steepest slope of a ramp (a smoothstep climbs at 1.5 times its average slope)
const DECK_THICKNESS = 0.9;
export { DECK_THICKNESS };

const PROFILE_TOLERANCE = 0.019; // metres of vertical interpolation error on a ramp
const rampLength = (layer, length) => Math.min(length / 2, (1.5 * layer * LAYER_HEIGHT) / MAX_GRADE);
const smooth = t => t * t * (3 - 2 * t);

/**
 * Deck height at distance s along an edge of the given length, for an OSM layer (0 = on the ground). The ramp is as long as
 * the grade limit needs; a bridge too short for that only rises as far as the limit allows, so it becomes a gentle hump.
 */
export function bridgeHeight(layer, s, length) {
  if (!(layer > 0) || !(length > 0)) return 0;
  const target = layer * LAYER_HEIGHT;
  const ramp = rampLength(layer, length);
  const peak = Math.min(target, (ramp * MAX_GRADE) / 1.5);
  const toEnd = Math.max(0, Math.min(s, length - s));
  return peak * smooth(Math.min(1, toEnd / ramp));
}

/** True for road features drawn as a raised deck. */
export const isBridge = road => Boolean(road.bridge) && road.layer > 0 && !road.tunnel;

/** Deck heights of the points of a road fragment (geometry in tile-local or world metres, in travel order). */
export function fragmentHeights(road) {
  const heights = [];
  let along = road.edgeStart ?? 0;
  road.geometry.forEach((point, index) => {
    if (index) along += Math.hypot(point[0] - road.geometry[index - 1][0], point[1] - road.geometry[index - 1][1]);
    heights.push(bridgeHeight(road.layer, along, road.edgeLength));
  });
  return heights;
}

/** Split an original strip segment only where its chord departs from the traffic curve. */
export function* bridgeRampSections(road) {
  const { layer, edgeLength, geometry } = road;
  if (!(layer > 0) || !(edgeLength > 0)) return;
  const ramp = rampLength(layer, edgeLength);
  const peak = bridgeHeight(layer, ramp, edgeLength);

  function* rampCuts(a, b) {
    // A cubic chord's greatest deviation occurs where slope = 6t(1-t) in normalized ramp coordinates.
    const slope = 3 * (a + b) - 2 * (a * a + a * b + b * b);
    const delta = Math.sqrt(Math.max(0, (1.5 - slope) / 6));
    let worst = PROFILE_TOLERANCE, split;
    for (const t of [0.5 - delta, 0.5 + delta]) {
      if (t <= a || t >= b) continue;
      const error = peak * Math.abs(smooth(t) - smooth(a) - (t - a) * slope);
      if (error > worst) { worst = error; split = t; }
    }
    if (split === undefined) return;
    yield* rampCuts(a, split);
    yield split;
    yield* rampCuts(split, b);
  }

  const descent = edgeLength - ramp;
  let start = road.edgeStart ?? 0;
  for (let segment = 0; segment + 1 < geometry.length; segment++) {
    const a = geometry[segment], b = geometry[segment + 1];
    const end = start + Math.hypot(b[0] - a[0], b[1] - a[1]);
    // Mapped vertices are rounded to centimetres. A sub-half-centimetre panel may collapse at world-space float precision.
    const interior = s => s > start + 0.005 && s < end - 0.005;
    const section = s => ({ segment, fraction: (s - start) / (end - start), height: bridgeHeight(layer, s, edgeLength) });
    let from = start;
    // Keep the level deck and both ramp ends exactly level where the traffic curve is constant.
    for (const to of [0, ramp, descent, edgeLength, end]) {
      if (to <= from || to > end) continue;
      const offset = to <= ramp ? 0 : descent;
      if (from >= offset && to <= offset + ramp) {
        for (const t of rampCuts((from - offset) / ramp, (to - offset) / ramp)) {
          const s = offset + t * ramp;
          if (interior(s)) yield section(s);
        }
      }
      if (interior(to)) yield section(to);
      from = to;
    }
    start = end;
  }
}

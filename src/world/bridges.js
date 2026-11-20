// Bridges and flyovers: a road tagged as a bridge (layer 1 or more) is lifted off the ground and ramps up from its ends.
// The tiles say where each fragment starts along its whole edge (edgeStart) and how long the edge is (edgeLength).
export const LAYER_HEIGHT = 5.5; // metres per OSM layer
const MAX_GRADE = 0.08;          // the steepest slope of a ramp (a smoothstep climbs at 1.5 times its average slope)
const DECK_THICKNESS = 0.9;
export { DECK_THICKNESS };

const smooth = t => t * t * (3 - 2 * t);

/**
 * Deck height at distance s along an edge of the given length, for an OSM layer (0 = on the ground). The ramp is as long as
 * the grade limit needs; a bridge too short for that only rises as far as the limit allows, so it becomes a gentle hump.
 */
export function bridgeHeight(layer, s, length) {
  if (!(layer > 0) || !(length > 0)) return 0;
  const target = layer * LAYER_HEIGHT;
  const ramp = Math.min(length / 2, (1.5 * target) / MAX_GRADE);
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

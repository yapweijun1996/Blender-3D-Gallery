// Composition measured from the anchor image: where each module sits and how the modules connect.
// `screen` is the plinth centre and width in the 1536x1024 anchor; `yaw` is the camera azimuth the
// module was modelled for (reports/<id>.json), so rotating by VIEW_YAW - yaw keeps its authored face.
export const VIEW_YAW = 43;
export const VIEW_ELEVATION = 35;
const PLINTH = 4.6;
const PIXELS_PER_UNIT = 100;
// Top of the shared two-tier plinth (source/common.py).
const PLINTH_TOP = 0.51;

export const MODULES = Object.freeze([
  { id: "warehouse", yaw: 41.02, screen: [815, 285, 700] },
  { id: "shop", yaw: -34.22, screen: [288, 455, 475] },
  { id: "bags", yaw: -43.83, screen: [768, 590, 515] },
  { id: "delivery", yaw: 39.35, screen: [1262, 510, 475] },
  { id: "payment", yaw: 41.35, screen: [372, 760, 387] },
  { id: "analytics", yaw: 49.24, screen: [765, 900, 345] },
  { id: "automation", yaw: 47.2, screen: [1145, 745, 374] },
]);

export const LINKS = Object.freeze([
  ["shop", "warehouse"], ["warehouse", "delivery"], ["shop", "bags"], ["delivery", "bags"],
  ["payment", "bags"], ["automation", "bags"], ["payment", "analytics"], ["analytics", "automation"],
]);

/** Ground position, uniform scale and rotation for each module. */
export function placements() {
  const yaw = VIEW_YAW * Math.PI / 180, flatten = Math.sin(VIEW_ELEVATION * Math.PI / 180);
  return MODULES.map(({ id, yaw: moduleYaw, screen: [x, y, width] }) => {
    const scale = width / PIXELS_PER_UNIT / (PLINTH * Math.SQRT2);
    const right = (x - 768) / PIXELS_PER_UNIT;
    // The anchor point is the plinth top, so step down to the ground before unflattening depth.
    const down = (y - 560 + PLINTH_TOP * scale * Math.cos(VIEW_ELEVATION * Math.PI / 180) * PIXELS_PER_UNIT) / PIXELS_PER_UNIT / flatten;
    return {
      id, scale,
      x: right * Math.cos(yaw) + down * Math.sin(yaw),
      z: -right * Math.sin(yaw) + down * Math.cos(yaw),
      rotation: (VIEW_YAW - moduleYaw) * Math.PI / 180,
      radius: PLINTH / 2 * scale,
    };
  });
}

/** Distance from a module centre to its rotated square plinth along a ground direction. */
function reach(place, dx, dz) {
  const cos = Math.cos(place.rotation), sin = Math.sin(place.rotation);
  return place.radius / Math.max(Math.abs(dx * cos - dz * sin), Math.abs(dx * sin + dz * cos));
}

/** Straight ground segments between plinth edges. */
export function linkSegments(places = placements()) {
  const byId = new Map(places.map(place => [place.id, place]));
  return LINKS.map(([from, to]) => {
    const a = byId.get(from), b = byId.get(to);
    const length = Math.hypot(b.x - a.x, b.z - a.z), dx = (b.x - a.x) / length, dz = (b.z - a.z) / length;
    // A small margin keeps the end node clear of the edge glow.
    const start = reach(a, dx, dz) + 0.14, end = length - reach(b, dx, dz) - 0.14;
    return { from, to, a: [a.x + dx * start, a.z + dz * start], b: [a.x + dx * end, a.z + dz * end] };
  });
}

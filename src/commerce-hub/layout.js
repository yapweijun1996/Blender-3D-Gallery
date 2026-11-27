// Composition traced from the 1536x1024 anchor image, in its own pixel coordinates.
// `yaw` is the camera azimuth each module was modelled for (reports/<id>.json), so rotating by
// VIEW_YAW - yaw keeps its authored face towards the shared camera.
export const VIEW_YAW = 43;
export const VIEW_ELEVATION = 30;
export const FRAME = Object.freeze({ width: 1536, height: 1024, pixelsPerUnit: 100 });
// Extra room above the anchor frame so a label fits over the tallest module.
export const HEADROOM = 64;

// Shared plinth (source/common.py): outer slab size, corner radius and half of its total height.
const PLINTH = 4.6, CORNER = 0.56, WAIST = 0.17;
export const PLINTH_TOP = 0.51;

// left/right: outermost plinth pixels; y: pixel height of those side corners.
// content: [width, height] of what stands on the plinth, where the anchor proportions it differently.
export const MODULES = Object.freeze([
  { id: "warehouse", yaw: 41.02, left: 467, right: 1157, y: 298, content: [0.9, 0.67] },
  { id: "shop", yaw: -34.22, left: 50, right: 516, y: 472 },
  { id: "bags", yaw: -43.83, left: 516, right: 1023, y: 597, content: [0.92, 0.9] },
  { id: "delivery", yaw: 39.35, left: 1026, right: 1491, y: 505, content: [0.99, 0.93] },
  { id: "payment", yaw: 41.35, left: 177, right: 563, y: 772 },
  { id: "analytics", yaw: 49.24, left: 594, right: 932, y: 920, content: [0.95, 0.84] },
  { id: "automation", yaw: 47.2, left: 958, right: 1340, y: 779, content: [0.94, 0.9] },
]);

// from, to, the two end pixels, which end carries the glowing node (0 or 1) and an optional bend point.
export const LINKS = Object.freeze([
  ["shop", "warehouse", [470, 410], [578, 357], 1],
  ["warehouse", "delivery", [1013, 374], [1100, 418], 0],
  ["shop", "bags", [401, 524], [522, 588], 0],
  ["delivery", "bags", [1133, 558], [1015, 590], 0, [1068, 598]],
  ["payment", "bags", [500, 718], [610, 664], 1],
  ["automation", "bags", [1025, 724], [915, 668], 1],
  ["payment", "analytics", [485, 823], [610, 892], 0],
  ["analytics", "automation", [912, 888], [1027, 828], 1],
]);

// Links run along the plinth sides, a little above the floor.
export const LINK_HEIGHT = 0.12;

const radians = degrees => degrees * Math.PI / 180;
const yaw = radians(VIEW_YAW), elevation = radians(VIEW_ELEVATION);
// Ground directions that appear as screen-right and screen-up.
const RIGHT = [Math.cos(yaw), -Math.sin(yaw)], BACK = [-Math.sin(yaw), -Math.cos(yaw)];
const across = x => (x - FRAME.width / 2) / FRAME.pixelsPerUnit;
const rise = y => (FRAME.height / 2 - y) / FRAME.pixelsPerUnit;

/** Ground position under an anchor pixel, for something `height` units above the floor. */
export function groundPoint([x, y], height = 0) {
  const side = across(x), depth = (rise(y) - height * Math.cos(elevation)) / Math.sin(elevation);
  return [side * RIGHT[0] + depth * BACK[0], side * RIGHT[1] + depth * BACK[1]];
}

/** Screen-right half extent of the unit-scale plinth after rotation. */
function halfExtent(rotation) {
  const inner = PLINTH / 2 - CORNER, turned = rotation - yaw;
  return inner * (Math.abs(Math.cos(turned)) + Math.abs(Math.sin(turned))) + CORNER;
}

/** Ground position, uniform scale and rotation for each module. */
export function placements() {
  return MODULES.map(module => {
    const rotation = radians(VIEW_YAW - module.yaw);
    const scale = (module.right - module.left) / FRAME.pixelsPerUnit / (2 * halfExtent(rotation));
    const [x, z] = groundPoint([(module.left + module.right) / 2, module.y], WAIST * scale);
    return { id: module.id, content: module.content ?? [1, 1], x, z, scale, rotation, radius: PLINTH / 2 * scale };
  });
}

/** True when a ground point lies on a module's rotated square plinth. */
export function onPlinth(place, [x, z], margin = 0) {
  const dx = x - place.x, dz = z - place.z, cos = Math.cos(place.rotation), sin = Math.sin(place.rotation);
  return Math.max(Math.abs(dx * cos - dz * sin), Math.abs(dx * sin + dz * cos)) <= place.radius + margin;
}

/** The traced floor paths between modules, with the point that carries each node. */
export function linkSegments() {
  return LINKS.map(([from, to, a, b, node, bend]) => {
    const points = (bend
      ? Array.from({ length: 13 }, (_, i) => {
        const t = i / 12, u = 1 - t;
        return [0, 1].map(k => u * u * a[k] + 2 * u * t * bend[k] + t * t * b[k]);
      })
      : [a, b]).map(pixel => groundPoint(pixel, LINK_HEIGHT));
    return { from, to, points, node: node ? points.at(-1) : points[0], nodeModule: node ? to : from };
  });
}

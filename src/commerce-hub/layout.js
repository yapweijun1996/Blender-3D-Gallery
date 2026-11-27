// Composition traced from the 1536x1024 anchor image, in its own pixel coordinates.
// `yaw` is the camera azimuth each module was modelled for (reports/<id>.json), so rotating by
// VIEW_YAW - yaw keeps its authored face towards the shared camera.
export const VIEW_YAW = 43;
export const VIEW_ELEVATION = 30;
export const FRAME = Object.freeze({ width: 1536, height: 1024, pixelsPerUnit: 100 });

// Shared plinth (source/common.py): outer slab size, corner radius and half of its total height.
const PLINTH = 4.6, CORNER = 0.56, WAIST = 0.255;
export const PLINTH_TOP = 0.51;

// left/right: outermost plinth pixels; y: pixel height of those side corners.
// label: centre of the label pill; pin: the dot its leader line points at.
// content: [width, height] of what stands on the plinth, where the anchor proportions it differently.
export const MODULES = Object.freeze([
  { id: "warehouse", yaw: 41.02, left: 470, right: 1168, y: 296, content: [0.9, 0.74], label: [711, 45], pin: [712, 143] },
  { id: "shop", yaw: -34.22, left: 50, right: 524, y: 462, label: [184, 185], pin: [196, 262] },
  { id: "bags", yaw: -43.83, left: 517, right: 1026, y: 603, content: [0.92, 0.9] },
  { id: "delivery", yaw: 39.35, left: 1027, right: 1498, y: 479, content: [0.99, 0.85], label: [1323, 224], pin: [1328, 312] },
  { id: "payment", yaw: 41.35, left: 179, right: 563, y: 759, label: [193, 628], pin: [196, 678] },
  { id: "analytics", yaw: 49.24, left: 596, right: 933, y: 890, content: [0.95, 0.84], label: [766, 766], pin: [766, 842] },
  { id: "automation", yaw: 47.2, left: 959, right: 1331, y: 739, content: [0.94, 0.9], label: [1355, 663], pin: [1353, 712] },
]);

// from, to, start pixel, end pixel and an optional bend point.
export const LINKS = Object.freeze([
  ["shop", "warehouse", [470, 418], [579, 357]],
  ["warehouse", "delivery", [1013, 375], [1102, 420]],
  ["shop", "bags", [399, 524], [541, 592]],
  ["delivery", "bags", [1133, 558], [1004, 598], [1066, 590]],
  ["payment", "bags", [497, 722], [610, 663]],
  ["automation", "bags", [913, 668], [1021, 722]],
  ["payment", "analytics", [485, 822], [626, 893]],
  ["analytics", "automation", [914, 883], [1029, 828]],
]);

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
    return { id: module.id, content: module.content ?? [1, 1], x, z, scale, rotation, radius: PLINTH / 2 * scale, label: module.label, pin: module.pin };
  });
}

/** Floor paths between modules, as ground points. */
export function linkSegments() {
  return LINKS.map(([from, to, a, b, bend]) => ({
    from, to,
    points: (bend
      ? Array.from({ length: 11 }, (_, i) => {
        const t = i / 10, u = 1 - t;
        return [0, 1].map(k => u * u * a[k] + 2 * u * t * bend[k] + t * t * b[k]);
      })
      : [a, b]).map(pixel => groundPoint(pixel, 0.04)),
  }));
}

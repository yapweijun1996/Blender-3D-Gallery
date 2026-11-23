import { buildTile } from "../tile-mesh.js";

const SUPPORT_DEPTH = .12;
const WALKWAY_IDS = ["774912614:0", "1552288080:0"];
const indices = Uint32Array.of(0, 1, 2, 3, 5, 4, 0, 3, 1, 1, 3, 4, 1, 4, 2, 2, 4, 5, 2, 5, 0, 0, 5, 3);

export function mergeWalkways(profile) {
  return WALKWAY_IDS.flatMap(id => {
    const footway = profile.crossings.find(feature => feature.edgeId === id && feature.kind === "pedestrian");
    const geometry = buildTile({ x: 0, z: 0, pedestrian: [{ geometry: footway.points }] }).ground;
    try {
      const vertices = geometry.attributes.position.array, index = geometry.index?.array;
      const vertex = i => vertices.subarray((index?.[i] ?? i) * 3, (index?.[i] ?? i) * 3 + 3);
      const panels = [];
      for (let i = 0; i < (index?.length ?? vertices.length / 3); i += 3) {
        const a = vertex(i), b = vertex(i + 1), c = vertex(i + 2);
        const up = (b[2] - a[2]) * (c[0] - a[0]) - (b[0] - a[0]) * (c[2] - a[2]);
        const ordered = up > 0 ? [a, b, c] : [a, c, b];
        const position = Float32Array.from([
          ...ordered.flatMap(point => [...point]),
          ...ordered.flatMap(([x, y, z]) => [x, y - SUPPORT_DEPTH, z]),
        ]);
        // A planar terrain mesh can retain rays but lose capsule support under sustained motion.
        // Give each exact pavement triangle the volume used by the player's contact solver.
        panels.push({ id: "footway", position, indices, convex: true });
      }
      return panels;
    } finally {
      geometry.dispose();
    }
  });
}

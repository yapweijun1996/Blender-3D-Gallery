import { buildTile } from "../tile-mesh.js";
import { pavementPanel } from "../pavement.js";

const WALKWAY_IDS = ["774912614:0", "1552288080:0"];

export function mergeWalkways(profile) {
  return WALKWAY_IDS.flatMap(id => {
    const footway = profile.crossings.find(feature => feature.edgeId === id && feature.kind === "pedestrian");
    const geometry = buildTile({ x: 0, z: 0, pedestrian: [{ geometry: footway.points }] }).ground;
    try {
      const vertices = geometry.attributes.position.array, index = geometry.index?.array;
      const vertex = i => vertices.subarray((index?.[i] ?? i) * 3, (index?.[i] ?? i) * 3 + 3);
      const panels = [];
      for (let i = 0; i < (index?.length ?? vertices.length / 3); i += 3) {
        panels.push(pavementPanel(vertex(i), vertex(i + 1), vertex(i + 2)));
      }
      return panels;
    } finally {
      geometry.dispose();
    }
  });
}

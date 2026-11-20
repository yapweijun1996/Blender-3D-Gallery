// Supertree Grove at Gardens by the Bay: the map gives the garden's outline but not the individual trees, so the trees are
// scattered inside the mapped outline (fixed seed, minimum spacing). The positions are approximate; the count follows the real grove (11 trees of 25 to 50 m).
export const GROVE_NAME = /Supertree Grove/i;
const MODELS = ["sg-supertree-tall", "sg-supertree-mid", "sg-supertree-short", "sg-supertree-mid", "sg-supertree-tall", "sg-supertree-short"];

const inside = (x, z, ring) => {
  let result = false;
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
    if ((ring[i][1] > z) !== (ring[j][1] > z) && x < (ring[j][0] - ring[i][0]) * (z - ring[i][1]) / (ring[j][1] - ring[i][1]) + ring[i][0]) result = !result;
  }
  return result;
};

/** World-space outlines of the grove from loaded tile data (the outline is cut at tile borders, so there can be several pieces). */
export function groveRings(tiles) {
  const rings = [];
  for (const tile of tiles) for (const park of tile.parks ?? []) {
    if (GROVE_NAME.test(park.name ?? "")) rings.push(park.geometry.map(([x, z]) => [x + tile.x * 250, z + tile.z * 250]));
  }
  return rings;
}

/** Up to `count` trees inside the outlines, at least `spacing` metres apart: [{ x, z, yaw, model }]. */
export function grovePlacements(rings, { count = 11, spacing = 17, seed = 2024 } = {}) {
  if (!rings.length) return [];
  const flat = rings.flat();
  const minX = Math.min(...flat.map(p => p[0])), maxX = Math.max(...flat.map(p => p[0]));
  const minZ = Math.min(...flat.map(p => p[1])), maxZ = Math.max(...flat.map(p => p[1]));
  let state = seed;
  const random = () => (state = (state * 1664525 + 1013904223) >>> 0) / 4294967296;
  const trees = [];
  for (let attempt = 0; attempt < 4000 && trees.length < count; attempt++) {
    const x = minX + random() * (maxX - minX), z = minZ + random() * (maxZ - minZ);
    if (!rings.some(ring => inside(x, z, ring))) continue;
    if (trees.some(tree => Math.hypot(tree.x - x, tree.z - z) < spacing)) continue;
    trees.push({ x, z, yaw: random() * Math.PI * 2, model: MODELS[trees.length % MODELS.length] });
  }
  return trees;
}

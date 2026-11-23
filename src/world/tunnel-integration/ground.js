/** World-space XZ bounds of a flat surface. The values match its float32 vertices. */
export function surfaceBounds({ position }) {
  let minX = Infinity, maxX = -Infinity, minZ = Infinity, maxZ = -Infinity;
  for (let index = 0; index < position.length; index += 3) {
    const x = position[index], z = position[index + 2];
    minX = Math.min(minX, x);
    maxX = Math.max(maxX, x);
    minZ = Math.min(minZ, z);
    maxZ = Math.max(maxZ, z);
  }
  return { minX, maxX, minZ, maxZ };
}

/** Four disjoint rectangles sharing the inner and outer perimeters exactly. */
export function splitGroundBounds(outer, cut) {
  const { minX, maxX, minZ, maxZ } = outer;
  const extents = [minX, maxX, minZ, maxZ, cut.minX, cut.maxX, cut.minZ, cut.maxZ];
  if (!extents.every(Number.isFinite) || !(minX <= cut.minX && cut.minX < cut.maxX && cut.maxX <= maxX &&
        minZ <= cut.minZ && cut.minZ < cut.maxZ && cut.maxZ <= maxZ)) {
    throw new RangeError('Ground cut must be a nonempty rectangle inside the ground');
  }
  return [
    { minX, maxX: cut.minX, minZ, maxZ },
    { minX: cut.maxX, maxX, minZ, maxZ },
    { minX: cut.minX, maxX: cut.maxX, minZ, maxZ: cut.minZ },
    { minX: cut.minX, maxX: cut.maxX, minZ: cut.maxZ, maxZ },
  ].filter(rectangle => rectangle.minX < rectangle.maxX && rectangle.minZ < rectangle.maxZ);
}

/** Tessellate the ordinary flat ground with its original upward face winding. */
export function groundSurface(rectangles, height = 0) {
  const position = new Float32Array(rectangles.length * 12);
  const indices = new Uint32Array(rectangles.length * 6);
  for (const [index, { minX, maxX, minZ, maxZ }] of rectangles.entries()) {
    position.set([
      minX, height, minZ, minX, height, maxZ, maxX, height, maxZ, maxX, height, minZ,
    ], index * 12);
    const start = index * 4;
    indices.set([start, start + 1, start + 2, start, start + 2, start + 3], index * 6);
  }
  return { id: 'ground', position, indices };
}

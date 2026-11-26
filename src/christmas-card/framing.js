// Orthographic fit from the actual animated bounds. Keep flight motion independent
// of the camera and leave enough margin for the bevels and the gentle idle float.
export function frameEnvelope(width, height, bodyWidth, bounds) {
  const scale = Math.min(width * .96 / bodyWidth, width * .96 / bounds.width, height * .98 / bounds.height);
  return { scale, halfWidth: width / (2 * scale), halfHeight: height / (2 * scale), centerY: (bounds.minY + bounds.maxY) / 2 };
}

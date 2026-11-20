// Heading-up minimap: the car is fixed near the bottom centre, the road ahead goes up. Pure transforms plus a canvas painter.
export const MAP_RANGE = 220; // metres shown from the car to the top edge

/** Map a world point to canvas pixels: `size` is { width, height }, the car sits at 60% of the height. */
export function toMinimap(point, car, heading, size, range = MAP_RANGE) {
  const dx = point.x - car.x, dz = point.z - car.z;
  const forward = dx * Math.sin(heading) + dz * Math.cos(heading), right = -dx * Math.cos(heading) + dz * Math.sin(heading);
  const scale = (size.height * 0.6) / range;
  return { x: size.width / 2 + right * scale, y: size.height * 0.6 - forward * scale };
}

/** Pull a point that lies outside the map in to its border along the line from the car (used for the mission target). */
export function clampToMap(position, size, margin = 8) {
  const cx = size.width / 2, cy = size.height * 0.6;
  const inside = position.x >= margin && position.x <= size.width - margin && position.y >= margin && position.y <= size.height - margin;
  if (inside) return { ...position, clamped: false };
  const dx = position.x - cx, dy = position.y - cy;
  const scale = Math.min(
    dx > 0 ? (size.width - margin - cx) / dx : dx < 0 ? (margin - cx) / dx : Infinity,
    dy > 0 ? (size.height - margin - cy) / dy : dy < 0 ? (margin - cy) / dy : Infinity,
  );
  return { x: cx + dx * scale, y: cy + dy * scale, clamped: true };
}

/** Paint the map: `edges` are road polylines in world metres, `vehicles` and `target` are { x, z }. */
export function paintMinimap(context, { size, car, heading, edges, vehicles, target, colors }) {
  context.clearRect(0, 0, size.width, size.height);
  context.fillStyle = colors.background;
  context.fillRect(0, 0, size.width, size.height);
  context.lineCap = "round";
  context.strokeStyle = colors.road;
  context.lineWidth = 2.2;
  for (const edge of edges) {
    if (edge.points.every(point => Math.hypot(point[0] - car.x, point[1] - car.z) > MAP_RANGE * 1.6)) continue;
    context.beginPath();
    edge.points.forEach(([x, z], index) => {
      const at = toMinimap({ x, z }, car, heading, size);
      if (index) context.lineTo(at.x, at.y); else context.moveTo(at.x, at.y);
    });
    context.stroke();
  }
  context.fillStyle = colors.traffic;
  for (const vehicle of vehicles) {
    const at = toMinimap(vehicle, car, heading, size);
    if (at.x < 0 || at.x > size.width || at.y < 0 || at.y > size.height) continue;
    context.fillRect(at.x - 1.5, at.y - 1.5, 3, 3);
  }
  if (target) {
    const at = clampToMap(toMinimap(target, car, heading, size), size);
    context.fillStyle = colors.target;
    context.beginPath();
    context.arc(at.x, at.y, at.clamped ? 4 : 6, 0, Math.PI * 2);
    context.fill();
  }
  // The car: an arrow pointing up.
  const x = size.width / 2, y = size.height * 0.6;
  context.fillStyle = colors.car;
  context.beginPath();
  context.moveTo(x, y - 7);
  context.lineTo(x + 5, y + 6);
  context.lineTo(x, y + 3);
  context.lineTo(x - 5, y + 6);
  context.closePath();
  context.fill();
}

import { TABLE, RAILS, POCKETS } from "./table.js";

// Ray/capsule intersections use the same authored rail segments as physics.
// This predicts the initial path only; it makes no post-impact or pot promise.
export function aimContact(balls, angle) {
  const cue = balls[0], dx = Math.cos(angle), dz = Math.sin(angle);
  let result = { distance: Infinity, kind: "boundary", label: "Table boundary" };
  const accept = (distance, kind, label, id) => {
    if (distance >= 0 && distance < result.distance) result = { distance, kind, label, ...(id === undefined ? {} : { id }) };
  };
  const circle = (x, z, radius) => {
    const rx = x - cue.x, rz = z - cue.z, t = rx * dx + rz * dz;
    if (rx * rx + rz * rz <= radius * radius && t > 1e-10) return 0;
    const discriminant = radius * radius - (rx * rx + rz * rz - t * t);
    if (discriminant < 0) return Infinity;
    const near = t - Math.sqrt(discriminant);
    return near >= 0 && t > 1e-10 ? near : Infinity;
  };
  for (const ball of balls) if (ball.id && !ball.pocketed)
    accept(circle(ball.x, ball.z, TABLE.radius * 2), "ball", `First contact: ball ${ball.id}`, ball.id);
  for (const r of RAILS) {
    accept(circle(r.ax, r.az, TABLE.radius), "cushion", "First contact: cushion");
    accept(circle(r.bx, r.bz, TABLE.radius), "cushion", "First contact: cushion");
    const sx = r.bx - r.ax, sz = r.bz - r.az, length = Math.hypot(sx, sz);
    const nx = -sz / length, nz = sx / length, direction = dx * nx + dz * nz;
    if (Math.abs(direction) < 1e-10) continue;
    const signed = (cue.x-r.ax)*nx + (cue.z-r.az)*nz;
    const projected = ((cue.x-r.ax)*sx + (cue.z-r.az)*sz)/(length*length);
    if (Math.abs(signed) <= TABLE.radius + 1e-12 && projected >= 0 && projected <= 1 && signed*direction < 0)
      accept(0, "cushion", "First contact: cushion");
    for (const side of [-1, 1]) {
      if (side*direction >= 0) continue;
      const t = (side * TABLE.radius - (cue.x-r.ax)*nx - (cue.z-r.az)*nz) / direction;
      const along = ((cue.x + t*dx-r.ax)*sx + (cue.z + t*dz-r.az)*sz) / (length*length);
      if (along >= 0 && along <= 1) accept(t, "cushion", "First contact: cushion");
    }
  }
  for (const p of POCKETS) accept(circle(p.x, p.z, TABLE.pocketRadius), "pocket", "Pocket opening");
  // Outside the playable cloth is explicitly a boundary, never a fake contact.
  if (!Number.isFinite(result.distance)) {
    for (const [position, direction, bound] of [[cue.x, dx, 1.3], [cue.z, dz, 0.7]])
      if (Math.abs(direction) > 1e-10) accept(((direction > 0 ? bound : -bound)-position)/direction, "boundary", "Table boundary");
  }
  return { ...result, x: cue.x + result.distance*dx, z: cue.z + result.distance*dz };
}

// Frictionless equal-mass estimate for the first ball contact: the object ball leaves along the
// line of centers and the cue ball along the tangent. Spin, friction and later collisions are ignored.
export function postContact(balls, angle, contact) {
  if (contact.kind !== "ball") return null;
  const target = balls.find((b) => b.id === contact.id);
  if (!target) return null;
  const dx = Math.cos(angle), dz = Math.sin(angle), nx = target.x - contact.x, nz = target.z - contact.z;
  const length = Math.hypot(nx, nz);
  if (length < 1e-9) return null;
  const ux = nx / length, uz = nz / length, dot = dx * ux + dz * uz;
  const tx = dx - dot * ux, tz = dz - dot * uz, tangent = Math.hypot(tx, tz);
  return {
    object: { x: ux, z: uz, scale: Math.max(0, dot) },
    cue: tangent > 1e-6 ? { x: tx / tangent, z: tz / tangent, scale: tangent } : null,
  };
}

export function shotFeedback(before, next, shot) {
  if (next.phase === "recovery") return next.message;
  const potted = shot.pockets.filter((p) => p.id !== 0).map((p) => p.id);
  const detail = potted.length ? `Potted: ${potted.join(", ")}. ` : "No object ball potted. ";
  const turn = next.phase === "finished" ? `Player ${next.winner + 1} wins. `
    : next.player === before.player ? `Player ${next.player + 1} continues. ` : `Player ${next.player + 1}'s turn. `;
  return detail + turn + next.message;
}

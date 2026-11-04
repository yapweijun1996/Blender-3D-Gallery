import { TABLE, POCKETS, RAILS } from "./table.js";
const R = TABLE.radius;
export function createShot(balls, direction, power) {
  const length = Math.hypot(direction.x, direction.z);
  if (
    !(length > 0) ||
    !Number.isFinite(length) ||
    !Number.isFinite(power) ||
    power <= 0 ||
    power > 1
  )
    throw new Error("Invalid shot");
  const cue = balls.find((b) => b.id === 0);
  if (!cue || cue.pocketed) throw new Error("Cue ball is unavailable");
  const speed = 0.18 + power * TABLE.maxSpeed;
  cue.vx = (direction.x / length) * speed;
  cue.vz = (direction.z / length) * speed;
  return {
    firstContact: null,
    pockets: [],
    tick: 0,
    elapsed: 0,
    settledFor: 0,
    done: false,
    invalid: null,
  };
}
// Sixteen equal disks: bounded adaptive substeps, impulse contacts and explicit pocket sensors.
// No spin/jump simulation is claimed. Rendering never feeds positions back into this solver.
export function stepPhysics(balls, shot, dt = TABLE.step) {
  if (shot.done || shot.invalid) return;
  const maxSpeed = Math.max(...balls.map((b) => Math.hypot(b.vx, b.vz)));
  const substeps = Math.max(2, Math.ceil((maxSpeed * dt) / (R / 2)));
  if (substeps > 16) {
    shot.invalid = "Simulation speed exceeded safe bounds";
    return;
  }
  const h = dt / substeps;
  for (let sub = 0; sub < substeps; sub++) {
    for (const b of balls) {
      if (b.pocketed) continue;
      const mx = b.vx * h,
        mz = b.vz * h,
        travel = Math.hypot(mx, mz);
      b.x += mx;
      b.z += mz;
      if (b.q && travel > 0) {
        const half = travel / R / 2,
          s = Math.sin(half) / travel,
          ax = -mz * s,
          az = mx * s,
          w = Math.cos(half),
          [qx, qy, qz, qw] = b.q;
        const q = [
          w * qx - az * qy + ax * qw,
          w * qy + az * qx - ax * qz,
          w * qz + ax * qy + az * qw,
          w * qw - ax * qx - az * qz,
        ];
        const length = Math.hypot(...q);
        b.q = q.map((n) => n / length);
      }
      const p = POCKETS.find(
        (p) => Math.hypot(b.x - p.x, b.z - p.z) < TABLE.pocketRadius,
      );
      if (p) {
        b.pocketed = true;
        b.vx = b.vz = 0;
        shot.pockets.push({ id: b.id, pocket: p.id, tick: shot.tick, sub });
        continue;
      }
      const speed = Math.hypot(b.vx, b.vz),
        next = Math.max(0, speed - 0.24 * h);
      if (speed > 0) {
        b.vx *= next / speed;
        b.vz *= next / speed;
      }
    }
    for (let iteration = 0; iteration < 5; iteration++) {
      for (let i = 0; i < balls.length; i++)
        for (let j = i + 1; j < balls.length; j++) {
          const a = balls[i],
            b = balls[j];
          if (a.pocketed || b.pocketed) continue;
          let dx = b.x - a.x,
            dz = b.z - a.z,
            d = Math.hypot(dx, dz);
          if (d >= R * 2) continue;
          const nx = d > 1e-9 ? dx / d : 1,
            nz = d > 1e-9 ? dz / d : 0,
            overlap = R * 2 - d;
          a.x -= nx * overlap * 0.5001;
          a.z -= nz * overlap * 0.5001;
          b.x += nx * overlap * 0.5001;
          b.z += nz * overlap * 0.5001;
          const relative = (b.vx - a.vx) * nx + (b.vz - a.vz) * nz;
          if (relative < 0) {
            if (shot.firstContact === null && (a.id === 0 || b.id === 0))
              shot.firstContact = a.id === 0 ? b.id : a.id;
            const impulse = (-(1 + 0.96) * relative) / 2;
            a.vx -= impulse * nx;
            a.vz -= impulse * nz;
            b.vx += impulse * nx;
            b.vz += impulse * nz;
          }
        }
      for (const b of balls) {
        if (b.pocketed) continue;
        for (const rail of RAILS) {
          const dx = rail.bx - rail.ax,
            dz = rail.bz - rail.az;
          const t = Math.max(
            0,
            Math.min(
              1,
              ((b.x - rail.ax) * dx + (b.z - rail.az) * dz) /
                (dx * dx + dz * dz),
            ),
          );
          const px = rail.ax + t * dx,
            pz = rail.az + t * dz,
            nx0 = b.x - px,
            nz0 = b.z - pz,
            d = Math.hypot(nx0, nz0);
          if (d >= R || d < 1e-9) continue;
          const nx = nx0 / d,
            nz = nz0 / d;
          b.x += nx * (R - d + 0.000001);
          b.z += nz * (R - d + 0.000001);
          const v = b.vx * nx + b.vz * nz;
          if (v < 0) {
            b.vx -= 1.82 * v * nx;
            b.vz -= 1.82 * v * nz;
          }
        }
        if (
          ![b.x, b.z, b.vx, b.vz].every(Number.isFinite) ||
          Math.abs(b.x) > 1.21 ||
          Math.abs(b.z) > 0.66
        )
          shot.invalid = "A ball left the calibrated table";
      }
    }
  }
  shot.tick++;
  shot.elapsed += dt;
  const moving = balls.some(
    (b) => !b.pocketed && Math.hypot(b.vx, b.vz) > 0.012,
  );
  shot.settledFor = moving ? 0 : shot.settledFor + dt;
  if (shot.settledFor > 0.3) {
    for (const b of balls) b.vx = b.vz = 0;
    shot.done = true;
  }
  if (shot.elapsed > 25) shot.invalid = "Shot did not settle safely";
}

import { TABLE, POCKETS, RAILS } from "./table.js";
const R = TABLE.radius;
const DIAMETER = 2 * R;

// First intersection of a relative linear path with a circle, normalized to [0, 1].
function impactFraction(x, z, dx, dz, radius) {
  const c = x * x + z * z - radius * radius;
  if (c <= 0) return 0;
  const a = dx * dx + dz * dz;
  if (!a) return null;
  const b = 2 * (x * dx + z * dz),
    discriminant = b * b - 4 * a * c;
  if (discriminant < 0) return null;
  const t = (-b - Math.sqrt(discriminant)) / (2 * a);
  return t >= 0 && t <= 1 ? t : null;
}

function pointSegmentDistanceSquared(px, pz, ax, az, bx, bz) {
  const dx = bx - ax,
    dz = bz - az,
    length = dx * dx + dz * dz;
  const t = length
    ? Math.max(0, Math.min(1, ((px - ax) * dx + (pz - az) * dz) / length))
    : 0;
  return (px - ax - t * dx) ** 2 + (pz - az - t * dz) ** 2;
}

function segmentDistanceSquared(ax, az, bx, bz, cx, cz, dx, dz) {
  const ux = bx - ax,
    uz = bz - az,
    vx = dx - cx,
    vz = dz - cz;
  const cross = ux * vz - uz * vx;
  if (Math.abs(cross) > 1e-14) {
    const wx = cx - ax,
      wz = cz - az;
    const t = (wx * vz - wz * vx) / cross,
      u = (wx * uz - wz * ux) / cross;
    if (t >= 0 && t <= 1 && u >= 0 && u <= 1) return 0;
  }
  return Math.min(
    pointSegmentDistanceSquared(ax, az, cx, cz, dx, dz),
    pointSegmentDistanceSquared(bx, bz, cx, cz, dx, dz),
    pointSegmentDistanceSquared(cx, cz, ax, az, bx, bz),
    pointSegmentDistanceSquared(dx, dz, ax, az, bx, bz),
  );
}

// A projected graze is safe only if neither ball reaches a pocket or cushion first.
function segmentReachesRail(x, z, endX, endZ) {
  const railLimit = (R - 1e-9) ** 2;
  return RAILS.some(
    (r) =>
      segmentDistanceSquared(x, z, endX, endZ, r.ax, r.az, r.bx, r.bz) <
      railLimit,
  );
}

function hasEarlierRail(starts, ends, i, time) {
  const x = starts[2 * i],
    z = starts[2 * i + 1];
  return segmentReachesRail(
    x,
    z,
    x + (ends[2 * i] - x) * time,
    z + (ends[2 * i + 1] - z) * time,
  );
}

function hasEarlierObstacle(starts, ends, i, time) {
  const x = starts[2 * i],
    z = starts[2 * i + 1];
  const endX = x + (ends[2 * i] - x) * time;
  const endZ = z + (ends[2 * i + 1] - z) * time;
  const pocketLimit = (TABLE.pocketRadius - 1e-9) ** 2;
  return (
    POCKETS.some(
      (p) =>
        pointSegmentDistanceSquared(p.x, p.z, x, z, endX, endZ) < pocketLimit,
    ) || hasEarlierRail(starts, ends, i, time)
  );
}

// Earliest entry into the cushion's capsule (segment plus round ends).
function railImpact(x, z, dx, dz) {
  let first = null;
  const consider = (time, nx, nz) => {
    if (time < 0 || time > 1 || dx * nx + dz * nz >= -1e-12) return;
    if (!first || time < first.time) first = { time, nx, nz };
  };
  for (const rail of RAILS) {
    if (Math.max(x, x + dx) + R < Math.min(rail.ax, rail.bx) ||
        Math.min(x, x + dx) - R > Math.max(rail.ax, rail.bx) ||
        Math.max(z, z + dz) + R < Math.min(rail.az, rail.bz) ||
        Math.min(z, z + dz) - R > Math.max(rail.az, rail.bz)) continue;
    const ex = rail.bx - rail.ax, ez = rail.bz - rail.az;
    const length = Math.hypot(ex, ez), tx = ex / length, tz = ez / length;
    const nx = -tz, nz = tx;
    const distance = (x - rail.ax) * nx + (z - rail.az) * nz;
    const speed = dx * nx + dz * nz;
    if (Math.abs(speed) > 1e-12) for (const sign of [-1, 1]) {
      const time = (sign * R - distance) / speed;
      const along = (x + dx * time - rail.ax) * tx + (z + dz * time - rail.az) * tz;
      if (along >= 0 && along <= length) consider(time, sign * nx, sign * nz);
    }
    for (const [px, pz] of [[rail.ax, rail.az], [rail.bx, rail.bz]]) {
      const time = impactFraction(x - px, z - pz, dx, dz, R);
      if (time === null) continue;
      const rx = x + dx * time - px, rz = z + dz * time - pz;
      const radius = Math.hypot(rx, rz);
      if (radius > 1e-9) consider(time, rx / radius, rz / radius);
    }
  }
  return first;
}

function rollBall(ball, mx, mz) {
  const travel = Math.hypot(mx, mz);
  if (!ball.q || !travel) return;
  const half = travel / R / 2,
    s = Math.sin(half) / travel;
  // For Y-up coordinates, the rotation at the cloth contact must oppose
  // translation: omega cross (0, -R, 0) = (-vx, 0, -vz).
  const ax = mz * s,
    az = -mx * s,
    w = Math.cos(half);
  const [qx, qy, qz, qw] = ball.q;
  const q = [
    w * qx - az * qy + ax * qw,
    w * qy + az * qx - ax * qz,
    w * qz + ax * qy + az * qw,
    w * qw - ax * qx - az * qz,
  ];
  const length = Math.hypot(...q);
  ball.q = q.map((n) => n / length);
}

function pocketOnPath(x, z, endX, endZ, startTime = 0) {
  let result = null;
  for (const pocket of POCKETS) {
    // Tangency without entry is not a pot.
    if (
      pointSegmentDistanceSquared(pocket.x, pocket.z, x, z, endX, endZ) >=
      TABLE.pocketRadius ** 2
    )
      continue;
    const time = impactFraction(
      x - pocket.x,
      z - pocket.z,
      endX - x,
      endZ - z,
      TABLE.pocketRadius,
    );
    if (time === null) continue;
    const absolute = startTime + time * (1 - startTime);
    if (!result || absolute < result.time)
      result = { time: absolute, pocket: pocket.id };
  }
  return result;
}
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

// A fast ball arriving at a cluster can trigger several impacts in one step.
// Give only those steps a smaller travel bound, so a redirected ball has time
// to encounter its next neighbour instead of using a deep endpoint overlap.
function hasCrowdedApproach(balls, dt) {
  for (const a of balls) {
    if (a.pocketed) continue;
    const speedA = Math.hypot(a.vx, a.vz);
    if (speedA < 0.15) continue;
    for (const b of balls) {
      if (a === b || b.pocketed) continue;
      const dx = b.x - a.x, dz = b.z - a.z;
      const reach = DIAMETER + (speedA + Math.hypot(b.vx, b.vz)) * dt;
      if (dx * dx + dz * dz > reach * reach ||
          dx * (b.vx - a.vx) + dz * (b.vz - a.vz) >= 0) continue;
      for (const c of balls) {
        if (c === a || c === b || c.pocketed) continue;
        const bx = c.x - b.x, bz = c.z - b.z;
        const ax = c.x - a.x, az = c.z - a.z;
        const limit = DIAMETER + (speedA + Math.hypot(b.vx, b.vz) + Math.hypot(c.vx, c.vz)) * dt;
        if (bx * bx + bz * bz <= limit * limit || ax * ax + az * az <= limit * limit) return true;
      }
    }
  }
  return false;
}
// Sixteen equal disks: bounded adaptive substeps, impulse contacts and explicit pocket sensors.
// No spin/jump simulation is claimed. Rendering never feeds positions back into this solver.
export function stepPhysics(balls, shot, dt = TABLE.step) {
  if (shot.done || shot.invalid) return;
  // Stable ID order also makes exact-time ties independent of caller array order.
  const ordered = balls.every((b, i) => i === 0 || balls[i - 1].id < b.id)
    ? balls
    : [...balls].sort((a, b) => a.id - b.id);
  const maxSpeed = Math.max(...balls.map((b) => Math.hypot(b.vx, b.vz)));
  let substeps = Math.max(2, Math.ceil((maxSpeed * dt) / (R / 2)));
  if (substeps > 16) {
    shot.invalid = "Simulation speed exceeded safe bounds";
    return;
  }
  if (hasCrowdedApproach(ordered, dt)) substeps = 16;
  const h = dt / substeps;
  const starts = new Float64Array(ordered.length * 2);
  const ends = new Float64Array(ordered.length * 2);
  for (let sub = 0; sub < substeps; sub++) {
    for (let i = 0; i < ordered.length; i++) {
      starts[i * 2] = ordered[i].x;
      starts[i * 2 + 1] = ordered[i].z;
    }
    for (const b of ordered) {
      if (b.pocketed) continue;
      const mx = b.vx * h,
        mz = b.vz * h;
      b.x += mx;
      b.z += mz;
      rollBall(b, mx, mz);
      const speed = Math.hypot(b.vx, b.vz),
        next = Math.max(0, speed - 0.24 * h);
      if (speed > 0) {
        b.vx *= next / speed;
        b.vz *= next / speed;
      }
    }
    for (let i = 0; i < ordered.length; i++) {
      ends[i * 2] = ordered[i].x;
      ends[i * 2 + 1] = ordered[i].z;
    }
    const pendingPockets = ordered.map((ball, i) => {
      if (ball.pocketed) return null;
      return pocketOnPath(starts[i * 2], starts[i * 2 + 1], ball.x, ball.z);
    });
    const redirectedPaths = new Map();
    const railRedirected = new Set();
    const railBeforePocket = (i, time) => {
      const path = redirectedPaths.get(i);
      if (!path || time <= path.time)
        return hasEarlierRail(starts, ends, i, time);
      const fraction = (time - path.time) / (1 - path.time),
        ball = ordered[i];
      return (
        hasEarlierRail(starts, ends, i, path.time) ||
        segmentReachesRail(
          path.x,
          path.z,
          path.x + (ball.x - path.x) * fraction,
          path.z + (ball.z - path.z) * fraction,
        )
      );
    };
    const flushPockets = (until) => {
      for (let i = 0; i < ordered.length; i++) {
        const event = pendingPockets[i],
          ball = ordered[i];
        if (
          !event ||
          event.time > until ||
          ball.pocketed ||
          railBeforePocket(i, event.time)
        )
          continue;
        ball.pocketed = true;
        ball.vx = ball.vz = 0;
        shot.pockets.push({
          id: ball.id,
          pocket: event.pocket,
          tick: shot.tick,
          sub,
          time: event.time,
        });
        pendingPockets[i] = null;
      }
    };
    const redirected = new Set();
    for (let iteration = 0; iteration < 5; iteration++) {
      const contacts = [];
      for (let i = 0; i < ordered.length; i++)
        for (let j = i + 1; j < ordered.length; j++) {
          const a = ordered[i],
            b = ordered[j];
          if (a.pocketed || b.pocketed) continue;
          const overlaps = Math.hypot(b.x - a.x, b.z - a.z) < DIAMETER;
          if (!overlaps && iteration > 0) continue;
          const sx = starts[j * 2] - starts[i * 2],
            sz = starts[j * 2 + 1] - starts[i * 2 + 1],
            dx = ends[j * 2] - ends[i * 2] - sx,
            dz = ends[j * 2 + 1] - ends[i * 2 + 1] - sz,
            hit = impactFraction(sx, sz, dx, dz, DIAMETER);
          // Crossing-and-exiting between endpoints is a graze, not a near miss.
          const swept = !overlaps && hit !== null && hit > 0;
          if (!overlaps && !swept) continue;
          contacts.push({ i, j, time: hit ?? 1, sx, sz, dx, dz });
        }
      contacts.sort(
        (a, b) =>
          a.time - b.time ||
          ordered[a.i].id - ordered[b.i].id ||
          ordered[a.j].id - ordered[b.j].id,
      );
      for (const { i, j, time, sx, sz, dx: motionX, dz: motionZ } of contacts) {
        const a = ordered[i],
          b = ordered[j];
        if (iteration === 0) flushPockets(time);
        if (a.pocketed || b.pocketed) continue;
        // Let the existing cushion pass resolve an earlier rail before this pair.
        if (
          iteration === 0 &&
          !redirected.has(i) &&
          !redirected.has(j) &&
          (hasEarlierRail(starts, ends, i, time) ||
            hasEarlierRail(starts, ends, j, time))
        )
          continue;
        if (
          iteration === 0 &&
          time > 0 &&
          time < 1 &&
          !redirected.has(i) &&
          !redirected.has(j) &&
          !hasEarlierObstacle(starts, ends, i, time) &&
          !hasEarlierObstacle(starts, ends, j, time)
        ) {
          const hitX = sx + motionX * time,
            hitZ = sz + motionZ * time;
          const length = Math.hypot(hitX, hitZ),
            nx = hitX / length,
            nz = hitZ / length;
          const relative = (b.vx - a.vx) * nx + (b.vz - a.vz) * nz;
          if (relative < -1e-9) {
            if (shot.firstContact === null && (a.id === 0 || b.id === 0))
              shot.firstContact = a.id === 0 ? b.id : a.id;
            const impulse = (-(1 + 0.96) * relative) / 2,
              remaining = h * (1 - time);
            const vx = impulse * nx,
              vz = impulse * nz;
            a.vx -= vx;
            a.vz -= vz;
            b.vx += vx;
            b.vz += vz;
            // Account for the changed velocity during the remainder of this substep.
            const aMoveX = ends[2 * i] - starts[2 * i],
              aMoveZ = ends[2 * i + 1] - starts[2 * i + 1];
            const bMoveX = ends[2 * j] - starts[2 * j],
              bMoveZ = ends[2 * j + 1] - starts[2 * j + 1];
            a.x -= vx * remaining;
            a.z -= vz * remaining;
            b.x += vx * remaining;
            b.z += vz * remaining;
            rollBall(a, -aMoveX, -aMoveZ);
            rollBall(a, aMoveX * time, aMoveZ * time);
            rollBall(
              a,
              aMoveX * (1 - time) - vx * remaining,
              aMoveZ * (1 - time) - vz * remaining,
            );
            rollBall(b, -bMoveX, -bMoveZ);
            rollBall(b, bMoveX * time, bMoveZ * time);
            rollBall(
              b,
              bMoveX * (1 - time) + vx * remaining,
              bMoveZ * (1 - time) + vz * remaining,
            );
            const aHitX = starts[2 * i] + aMoveX * time,
              aHitZ = starts[2 * i + 1] + aMoveZ * time,
              bHitX = starts[2 * j] + bMoveX * time,
              bHitZ = starts[2 * j + 1] + bMoveZ * time;
            redirectedPaths.set(i, { time, x: aHitX, z: aHitZ });
            redirectedPaths.set(j, { time, x: bHitX, z: bHitZ });
            pendingPockets[i] = pocketOnPath(aHitX, aHitZ, a.x, a.z, time);
            pendingPockets[j] = pocketOnPath(bHitX, bHitZ, b.x, b.z, time);
            redirected.add(i);
            redirected.add(j);
          }
          continue;
        }
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
          redirected.add(i);
          redirected.add(j);
        }
      }
      if (iteration === 0) flushPockets(1);
      for (let i = 0; i < ordered.length; i++) {
        const b = ordered[i];
        if (b.pocketed) continue;
        // On the first pass, resolve a cushion at its actual contact time. The
        // endpoint projection below remains the fallback for dense contacts.
        if (iteration === 0 && !redirected.has(i) &&
            Math.abs(b.x - ends[2 * i]) < 1e-10 &&
            Math.abs(b.z - ends[2 * i + 1]) < 1e-10) {
          const x = starts[2 * i], z = starts[2 * i + 1];
          const mx = b.x - x, mz = b.z - z;
          const hit = (mx || mz) && railImpact(x, z, mx, mz);
          if (hit) {
            const { time, nx, nz } = hit;
            const remaining = 1 - time, normalMove = mx * nx + mz * nz;
            const postX = (mx - 1.82 * normalMove * nx) * remaining;
            const postZ = (mz - 1.82 * normalMove * nz) * remaining;
            const hitX = x + mx * time, hitZ = z + mz * time;
            b.x = hitX + postX;
            b.z = hitZ + postZ;
            const normalVelocity = b.vx * nx + b.vz * nz;
            if (normalVelocity < 0) {
              b.vx -= 1.82 * normalVelocity * nx;
              b.vz -= 1.82 * normalVelocity * nz;
            }
            rollBall(b, -mx, -mz);
            rollBall(b, mx * time, mz * time);
            rollBall(b, postX, postZ);
            redirectedPaths.set(i, { time, x: hitX, z: hitZ });
            pendingPockets[i] = pocketOnPath(hitX, hitZ, b.x, b.z, time);
            redirected.add(i);
            railRedirected.add(i);
          }
        }
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
      if (iteration === 0) {
        // When a rail preceded a pocket candidate, use the corrected endpoint.
        for (let i = 0; i < ordered.length; i++) {
          const event = pendingPockets[i],
            ball = ordered[i];
          if (!event || ball.pocketed) continue;
          const path = redirectedPaths.get(i);
          const sweptPocket = railRedirected.has(i) && path && event.time >= path.time &&
            !segmentReachesRail(path.x, path.z, ball.x, ball.z)
            ? POCKETS.find((p) => p.id === event.pocket) : null;
          const pocket = sweptPocket || POCKETS.find(
            (p) => Math.hypot(ball.x - p.x, ball.z - p.z) < TABLE.pocketRadius,
          );
          if (pocket) {
            ball.pocketed = true;
            ball.vx = ball.vz = 0;
            shot.pockets.push({
              id: ball.id,
              pocket: pocket.id,
              tick: shot.tick,
              sub,
              time: sweptPocket ? event.time : 1,
            });
          }
          pendingPockets[i] = null;
        }
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

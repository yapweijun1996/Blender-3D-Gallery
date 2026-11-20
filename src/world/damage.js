import { BufferAttribute, BufferGeometry, CanvasTexture, Points, PointsMaterial } from "three";

// What damage looks like: smoke from the bonnet once the car is hurt, and a dead engine when it is wrecked.
export const SMOKE_FROM = 0.4;   // damage at which smoke starts
export const STALL_AT = 0.95;    // damage at which the engine dies (repair or right the car to restart)

/** { smoke, stalled } for a damage value 0 to 1: smoke is 0 to 1 (strength), stalled disables the throttle. */
export function damageEffects(damage) {
  const value = Math.max(0, Math.min(1, Number.isFinite(damage) ? damage : 0));
  return { smoke: value < SMOKE_FROM ? 0 : Math.min(1, (value - SMOKE_FROM) / (1 - SMOKE_FROM)), stalled: value >= STALL_AT };
}

/** A small puff system: grey points that rise and fade from a point in front of the car. */
export function createSmoke(scene, capacity = 36) {
  const positions = new Float32Array(capacity * 3), ages = new Float32Array(capacity).fill(-1);
  const geometry = new BufferGeometry();
  geometry.setAttribute("position", new BufferAttribute(positions, 3));
  // A soft round puff (a point is a square otherwise); skipped where there is no canvas, as in Node tests.
  let map = null;
  if (typeof document !== "undefined") {
    const canvas = document.createElement("canvas");
    canvas.width = canvas.height = 64;
    const context = canvas.getContext("2d");
    const gradient = context.createRadialGradient(32, 32, 2, 32, 32, 31);
    gradient.addColorStop(0, "rgba(255,255,255,0.9)");
    gradient.addColorStop(1, "rgba(255,255,255,0)");
    context.fillStyle = gradient;
    context.fillRect(0, 0, 64, 64);
    map = new CanvasTexture(canvas);
  }
  const material = new PointsMaterial({ color: 0x777777, size: 1.2, transparent: true, opacity: 0.5, depthWrite: false, sizeAttenuation: true, map });
  const points = new Points(geometry, material);
  points.frustumCulled = false;
  points.visible = false;
  scene.add(points);
  let spawnClock = 0, cursor = 0;
  const LIFE = 1.8;

  return {
    points,
    /** Advance the puffs. `source` is { x, y, z } where smoke is made, `strength` 0 to 1 from damageEffects. */
    update(dt, source, strength) {
      spawnClock += dt * (3 + strength * 14);
      while (strength > 0 && spawnClock >= 1) {
        spawnClock -= 1;
        const i = cursor++ % capacity;
        ages[i] = 0;
        positions.set([source.x + (Math.random() - 0.5) * 0.5, source.y, source.z + (Math.random() - 0.5) * 0.5], i * 3);
      }
      if (strength <= 0) spawnClock = 0;
      let alive = 0;
      for (let i = 0; i < capacity; i++) {
        if (ages[i] < 0) continue;
        ages[i] += dt;
        if (ages[i] > LIFE) { ages[i] = -1; positions[i * 3 + 1] = -100; continue; }
        positions[i * 3 + 1] += dt * (1.2 + strength);
        alive++;
      }
      geometry.attributes.position.needsUpdate = true;
      material.size = 1 + strength * 1.6;
      points.visible = alive > 0;
      return alive;
    },
    dispose() { scene.remove(points); geometry.dispose(); map?.dispose(); material.dispose(); },
  };
}

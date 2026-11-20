// Adaptive resolution: if frames come slowly the renderer drops its pixel ratio in steps, and it raises it again when there is headroom.
export function createQualityGovernor({ initial, min = 0.6, target = 40, windowSeconds = 2.5, onChange }) {
  let ratio = initial, frames = 0, elapsed = 0, previous = null, healthy = 0;
  return {
    get ratio() { return ratio; },
    /** Call once per rendered frame with a timestamp in milliseconds (performance.now or the requestAnimationFrame time). */
    update(now) {
      if (previous === null) { previous = now; return; }
      const delta = (now - previous) / 1000;
      previous = now;
      // A long pause (tab hidden, debugger) must not count as slow frames.
      if (delta > 1.5) { frames = 0; elapsed = 0; return; }
      frames++; elapsed += delta;
      if (elapsed < windowSeconds) return;
      const fps = frames / elapsed;
      frames = 0; elapsed = 0;
      if (fps < target * 0.75 && ratio > min + 1e-6) {
        ratio = Math.max(min, ratio * 0.8); healthy = 0; onChange?.(ratio);
      } else if (fps > target * 1.4 && ratio < initial - 1e-6) {
        healthy++;
        if (healthy >= 2) { ratio = Math.min(initial, ratio * 1.15); healthy = 0; onChange?.(ratio); }
      } else healthy = 0;
    },
  };
}

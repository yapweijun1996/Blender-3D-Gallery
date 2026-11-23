import { installTunnelColliders } from '../tunnel-prototype/colliders.js';
import { splitGroundBounds } from './ground.js';

/** Own the ordinary ground or the same surrounding ground plus the streamed cut. */
export function createStreamedTunnelGround(physics, { bounds, surfaces, halfWidth = 60000, halfDepth = 60000 }) {
  const outer = { minX: -halfWidth, maxX: halfWidth, minZ: -halfDepth, maxZ: halfDepth };
  const outside = splitGroundBounds(outer, bounds);
  // Rapier rounds each large box's center and half-extent to float32 separately.
  // A small contact margin under the patch's flat apron keeps those seams supported.
  const margin = Math.max(halfWidth, halfDepth) * 2 ** -22;
  const outsideWithMargin = outside.map(({ minX, maxX, minZ, maxZ }) => ({
    minX: Math.max(outer.minX, minX - margin),
    maxX: Math.min(outer.maxX, maxX + margin),
    minZ: Math.max(outer.minZ, minZ - margin),
    maxZ: Math.min(outer.maxZ, maxZ + margin),
  }));

  function installGround(panels) {
    const boxes = [];
    function dispose() {
      for (const collider of boxes.splice(0).reverse()) physics.removeStatic(collider);
    }
    try {
      for (const { minX, maxX, minZ, maxZ } of panels) {
        boxes.push(physics.addGround({
          x: (minX + maxX) / 2, z: (minZ + maxZ) / 2,
          halfWidth: (maxX - minX) / 2, halfDepth: (maxZ - minZ) / 2,
        }));
      }
    } catch (error) {
      dispose();
      throw error;
    }
    return dispose;
  }

  // Outside support must stay in Rapier's query index through a patch swap.
  // New colliders become queryable on the next physics step.
  const disposeExterior = installGround(outsideWithMargin);
  let active = false;
  let disposeCurrent;
  try {
    disposeCurrent = installGround([bounds]);
  } catch (error) {
    disposeExterior();
    throw error;
  }
  return {
    get active() { return active; },
    setActive(wanted) {
      if (!disposeCurrent || wanted === active) return;
      // Install first so a failed update leaves the previous support fully intact.
      const disposeNext = wanted ? installTunnelColliders(physics, surfaces) : installGround([bounds]);
      disposeCurrent();
      disposeCurrent = disposeNext;
      active = wanted;
    },
    dispose() {
      disposeCurrent?.();
      disposeExterior();
      disposeCurrent = null;
      active = false;
    },
  };
}

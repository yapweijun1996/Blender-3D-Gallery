import { createFortCanningActivation } from './activation.js';
import { createStreamedTunnelGround } from './colliders.js';
import overlay from './fort-canning-runtime-overlay.json' with { type: 'json' };

// Includes the 40 m apron around the mapped carriageways.
const BOUNDS = { minX: -1850, maxX: -1170, minZ: -1720, maxZ: -1230 };
const PRELOAD_DISTANCE = 800;

export function createWorldFortCanning({ physics, signal, scene, flatGround, tiles, fetchTile, makeEntry, setColliders, disposeEntry }) {
  let entries = new Map(), retryArmed = false;
  const activation = createFortCanningActivation({
    physics, signal, safetyBounds: BOUNDS, requiredTileKeys: overlay.requiredTiles,
    async prepare(loadingSignal) {
      const [{ prepareFortCanningRoute }, { createFortCanningVisuals }] = await Promise.all([
        import('./route.js'), import('./visuals.js'),
      ]);
      const route = await prepareFortCanningRoute(fetchTile, loadingSignal);
      const road = createFortCanningVisuals(route.geometry, flatGround.material);
      const prepared = new Map();
      function dispose() {
        for (const [key, entry] of prepared) {
          if (tiles.get(key) === entry) tiles.delete(key);
          disposeEntry(entry);
        }
        prepared.clear();
        road.dispose();
        flatGround.visible = true;
      }
      try {
        for (const [key, data] of route.tiles) {
          const entry = makeEntry(data, {
            paint: overlay.paint, visualOnly: overlay.tiles[key]?.visualOnly,
            buildingBase: building => building.id === 719635727 ? 3 : 0,
          });
          prepared.set(key, entry);
        }
      } catch (error) {
        dispose();
        throw error;
      }
      entries = prepared;
      function publish() {
        scene.add(road.group);
        for (const entry of prepared.values()) scene.add(entry.group);
        for (const [key, entry] of prepared) {
          const previous = tiles.get(key);
          if (previous) disposeEntry(previous);
          tiles.set(key, entry);
        }
        flatGround.visible = false;
      }
      return { ...route, visuals: { publish, dispose } };
    },
    createGround(world, geometry) {
      const ground = createStreamedTunnelGround(world, geometry);
      return {
        setActive(wanted) {
          ground.setActive(wanted);
          for (const entry of entries.values()) setColliders(entry, wanted);
        },
        dispose() {
          for (const entry of entries.values()) setColliders(entry, false);
          ground.dispose();
        },
      };
    },
  });

  function beforePhysics(state, dt, occupants) {
    if (activation.status === 'active') return;
    const { x, z } = state.position;
    const distance = Math.hypot(Math.max(BOUNDS.minX - x, x - BOUNDS.maxX, 0), Math.max(BOUNDS.minZ - z, z - BOUNDS.maxZ, 0));
    const near = distance <= PRELOAD_DISTANCE;
    const frame = { player: { position: state.position, radius: 7, speed: state.speed }, dt };
    if (near && activation.status === 'idle') void activation.preload();
    if (activation.canRetry) {
      // Spend the one retry on a later approach or once the vehicle has driven clear of the protected patch.
      if (!near || distance === 0) retryArmed = true;
      else if (retryArmed) {
        frame.occupants = occupants();
        void activation.retry(frame);
        if (activation.status === 'preparing') retryArmed = false;
      }
    }
    if (activation.status === 'ready' || activation.status === 'staged') {
      frame.occupants = occupants();
      activation.beginFrame(frame);
    }
  }
  return { activation, beforePhysics };
}

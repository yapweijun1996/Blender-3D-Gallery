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
      const prepared = new Map(), replaced = new Map();
      const ordinaryGrassVisible = flatGround.visible;
      let disposed = false;
      function disposeEntries(owned) {
        const errors = [];
        for (const entry of owned) {
          try { disposeEntry(entry); }
          catch (error) { errors.push(error); }
        }
        if (errors.length) throw new AggregateError(errors, 'Fort Canning tile cleanup failed');
      }
      function dispose() {
        if (disposed) return;
        disposed = true;
        for (const [key, entry] of prepared) {
          if (tiles.get(key) !== entry) continue;
          const previous = replaced.get(key);
          if (previous) tiles.set(key, previous.entry);
          else tiles.delete(key);
        }
        for (const { entry, visible } of replaced.values()) entry.group.visible = visible;
        replaced.clear();
        const owned = [...prepared.values()];
        prepared.clear();
        flatGround.visible = ordinaryGrassVisible;
        try { disposeEntries(owned); }
        finally { road.dispose(); }
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
        for (const [key, entry] of prepared) {
          scene.add(entry.group);
          if (disposed) return;
          const previous = tiles.get(key);
          if (previous) replaced.set(key, { entry: previous, visible: previous.group.visible });
          tiles.set(key, entry);
          if (previous) previous.group.visible = false;
        }
        if (!disposed) flatGround.visible = false;
      }
      function commit() {
        const obsolete = [...replaced.values()].map(({ entry }) => entry);
        replaced.clear();
        disposeEntries(obsolete);
      }
      return { ...route, visuals: { publish, commit, dispose } };
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

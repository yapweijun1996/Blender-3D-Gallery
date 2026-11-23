import { createStreamedTunnelGround } from './colliders.js';

const REQUIRED_SURFACES = ['road', 'terrain', 'walls', 'ceiling', 'cover', 'portals'];
const GROUND_EXTENT = 60000;
const MOTION_MARGIN = 0.25;

function validBounds(bounds) {
  return bounds && [bounds.minX, bounds.maxX, bounds.minZ, bounds.maxZ].every(Number.isFinite) &&
    bounds.minX < bounds.maxX && bounds.minZ < bounds.maxZ;
}

function contains(outer, inner) {
  return outer.minX <= inner.minX && inner.maxX <= outer.maxX && outer.minZ <= inner.minZ && inner.maxZ <= outer.maxZ;
}

function validSurface({ position, indices }) {
  return position instanceof Float32Array && position.length >= 9 && position.length % 3 === 0 && position.every(Number.isFinite) &&
    indices instanceof Uint32Array && indices.length >= 3 && indices.length % 3 === 0 && indices.every(index => index < position.length / 3);
}

function clearForFrame(bounds, frame) {
  if (!bounds || !frame?.player) return false;
  const { player, occupants = [], dt = 0 } = frame;
  if (!Number.isFinite(dt) || dt < 0 || !Array.isArray(occupants)) return false;
  return [player, ...occupants].every(occupant => {
    const { position, radius, speed = 0 } = occupant ?? {};
    if (![position?.x, position?.z, radius, speed].every(Number.isFinite) || radius < 0 || speed < 0) return false;
    const dx = Math.max(bounds.minX - position.x, position.x - bounds.maxX, 0);
    const dz = Math.max(bounds.minZ - position.z, position.z - bounds.maxZ, 0);
    // Rapier may also advance using the fractional time carried from the previous frame.
    return Math.hypot(dx, dz) > radius + speed * Math.max(dt, 0.1) + MOTION_MARGIN;
  });
}

/** Own the session ground and publish the prepared Fort Canning bundle at a safe frame boundary. */
export function createFortCanningActivation({ physics, signal, safetyBounds, requiredTileKeys, prepare,
  createGround = createStreamedTunnelGround }) {
  const controller = new AbortController();
  const worldBounds = { minX: -GROUND_EXTENT, maxX: GROUND_EXTENT, minZ: -GROUND_EXTENT, maxZ: GROUND_EXTENT };
  let ordinary = signal?.aborted ? null : physics.addGround({ halfWidth: GROUND_EXTENT, halfDepth: GROUND_EXTENT });
  let status = 'idle', attempts = 0, failure = null, loading = null;
  let candidate = null, stagedGround = null, available = null;

  function removeOrdinary() {
    if (!ordinary) return;
    physics.removeStatic(ordinary);
    ordinary = null;
  }

  function unstage() {
    const ground = stagedGround;
    stagedGround = null;
    ground?.dispose();
  }

  function releaseCandidate() {
    const bundle = candidate;
    candidate = null;
    try {
      bundle?.visuals?.dispose?.();
    } finally {
      unstage();
    }
  }

  function fail(error) {
    if (status === 'disposed') return;
    status = 'failed';
    failure = error;
    try {
      releaseCandidate();
    } catch (cleanupError) {
      failure = new AggregateError([error, cleanupError], 'Fort Canning activation and cleanup failed');
    }
  }

  function validate(bundle) {
    const { geometry, overlay, tiles, visuals } = bundle ?? {};
    if (!validBounds(safetyBounds) || !contains(worldBounds, safetyBounds) || !validBounds(geometry?.bounds) ||
        !contains(safetyBounds, geometry.bounds) || !Array.isArray(geometry.surfaces) ||
        !geometry.surfaces.every(surface => surface && validSurface(surface)) ||
        !REQUIRED_SURFACES.every(id => geometry.surfaces.some(surface => surface.id === id))) {
      throw new Error('Fort Canning geometry is incomplete or outside its fixed safety bounds');
    }
    if (!overlay || typeof overlay !== 'object' || Array.isArray(overlay) || !(tiles instanceof Map) || !Array.isArray(requiredTileKeys) ||
        !requiredTileKeys.every(key => {
          const tile = tiles.get(key);
          return tile && typeof tile === 'object' && !Array.isArray(tile);
        })) {
      throw new Error('Fort Canning overlay dependencies are incomplete');
    }
    if (typeof visuals?.publish !== 'function' || typeof visuals.dispose !== 'function') {
      throw new Error('Fort Canning visuals must support publication and rollback');
    }
  }

  // Prepare must leave the scene unchanged. Its visuals.dispose also rolls back a partial publish.
  function preload() {
    if (status === 'preparing') return loading;
    if (status !== 'idle') return Promise.resolve(status === 'ready' || status === 'staged' || status === 'active');
    status = 'preparing';
    attempts++;
    loading = Promise.resolve().then(() => {
      controller.signal.throwIfAborted();
      return prepare(controller.signal);
    }).then(bundle => {
      if (status === 'disposed') {
        bundle?.visuals?.dispose?.();
        return false;
      }
      candidate = bundle;
      validate(bundle);
      candidate = { ...bundle, tiles: new Map(bundle.tiles) };
      status = 'ready';
      return true;
    }).catch(error => {
      if (status !== 'disposed') fail(error);
      return false;
    });
    return loading;
  }

  function beginFrame(frame) {
    if (status !== 'ready' && status !== 'staged') return;
    if (!clearForFrame(candidate.geometry.bounds, frame)) {
      if (status === 'staged') {
        try {
          unstage();
          status = 'ready';
        } catch (error) {
          fail(error);
        }
      }
      return;
    }
    if (status === 'staged') return;
    try {
      stagedGround = createGround(physics, candidate.geometry);
      stagedGround.setActive(true);
      status = 'staged';
    } catch (error) {
      fail(error);
    }
  }

  function afterPhysics({ substeps } = {}) {
    if (status !== 'staged' || !Number.isInteger(substeps) || substeps <= 0) return available;
    try {
      const { visuals, ...bundle } = candidate;
      visuals.publish();
      if (status !== 'staged') return available;
      // Keep the original plane until the cut and its exterior panels are in Rapier's query index.
      removeOrdinary();
      available = bundle;
      status = 'active';
    } catch (error) {
      fail(error);
    }
    return available;
  }

  function retry(frame) {
    if (status !== 'failed' || attempts >= 2 || !validBounds(safetyBounds) || !clearForFrame(safetyBounds, frame)) return Promise.resolve(false);
    failure = null;
    status = 'idle';
    return preload();
  }

  function dispose() {
    if (status === 'disposed') return;
    status = 'disposed';
    available = null;
    signal?.removeEventListener('abort', dispose);
    controller.abort();
    try {
      releaseCandidate();
    } finally {
      removeOrdinary();
    }
  }

  if (signal?.aborted) dispose();
  else signal?.addEventListener('abort', dispose, { once: true });

  return {
    preload, beginFrame, afterPhysics, retry, dispose,
    get status() { return status; },
    get available() { return available; },
    get failure() { return failure; },
  };
}

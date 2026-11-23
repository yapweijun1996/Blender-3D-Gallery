import profile from '../../../scripts/world/fort-canning-integration.json' with { type: 'json' };
import overlay from './fort-canning-runtime-overlay.json' with { type: 'json' };
import { createFortCanningMergeGeometry } from './merge-geometry.js';
import { fortCanningTrafficRoads } from './traffic-roads.js';

export const FORT_CANNING_TILES = Object.freeze(overlay.requiredTiles.slice());
const SOURCE_DIGESTS = new Map(profile.source.tiles.map(({ key, sha256 }) => [key, sha256]));
const encoder = new TextEncoder();
const TERMINAL_SIGNAL = 408999681;
const TERMINAL_STOP_OFFSETS = new Map([
  ['888048851:2', 15],
  ['474300998:5', 27],
  ['666009287:1', 18],
]);
const OVERLAY_LAYERS = ['roads', 'kerbs', 'junctions', 'crossings'];

async function applyTileOverlay(key, tile) {
  const [x, z] = key.split('_').map(Number);
  if (!tile || tile.x !== x || tile.z !== z) {
    throw new Error('Missing Fort Canning tile ' + key);
  }
  const additions = overlay.tiles[key];
  const expected = additions?.baseSha256 ?? SOURCE_DIGESTS.get(key);
  const hash = await crypto.subtle.digest('SHA-256', encoder.encode(JSON.stringify(tile)));
  const digest = Array.from(new Uint8Array(hash), byte => byte.toString(16).padStart(2, '0')).join('');
  if (digest !== expected) throw new Error('Fort Canning tile does not match the pinned geometry: ' + key);
  if (!additions) return tile;

  const combined = { ...tile };
  for (const layer of OVERLAY_LAYERS) combined[layer] = [...tile[layer], ...additions[layer]];
  return combined;
}

/** Resolve all six map dependencies before producing a candidate scene or road graph. */
export async function prepareFortCanningRoute(fetchTile, signal) {
  const tiles = new Map(await Promise.all(FORT_CANNING_TILES.map(async key => {
    const original = await fetchTile(key, signal);
    return [key, await applyTileOverlay(key, original)];
  })));
  signal.throwIfAborted();

  const geometry = createFortCanningMergeGeometry(profile);
  const options = fortCanningTrafficRoads(profile, geometry.alignment, tiles.values());
  const trafficOptions = {
    ...options,
    forwardMovements: overlay.movements,
    signalApproachChains: overlay.signalApproaches.filter(({ signal }) => signal === TERMINAL_SIGNAL)
      .map(({ edges }) => ({ edges, stopOffset: TERMINAL_STOP_OFFSETS.get(edges.at(-1)) })),
  };
  return { tiles, geometry, trafficOptions, overlay };
}

export const shellAssetPaths = {
  floor: 'models/mall-floor-tile/exports/mall-floor-tile-module.glb',
  cornerTile: 'models/mall-floor-corner-tile/exports/mall-floor-corner-tile.glb',
  floorEdge: 'models/mall-floor-edge-trim/exports/mall-floor-edge-trim.glb',
  mitredTrim: 'models/mall-floor-mitred-trim/exports/mall-floor-mitred-trim.glb',
  wall: 'models/mall-solid-wall/exports/mall-solid-wall.glb',
  wallCorner: 'models/mall-wall-corner/exports/mall-wall-corner.glb',
  ceiling: 'models/mall-ceiling-panel/exports/mall-ceiling-panel-module.glb',
};

const columns = [-3.6, -2.4, -1.2, 0, 1.2, 2.4, 3.6];
const floorRows = [-2.4, -1.2, 0, 1.2, 2.4];
const quarterTurn = Math.PI / 2;

export const shellLayout = {
  floor: columns.flatMap(x => floorRows.map(z => ({
    id: x === 3.6 && z === 2.4 ? 'cornerTile' : 'floor', x, y: -.03, z,
  }))),
  trim: [
    ...columns.slice(0, -1).map(x => ({ id: 'floorEdge', x, y: 0, z: 3.03 })),
    ...floorRows.slice(0, -1).map(z => ({ id: 'floorEdge', x: 4.23, y: 0, z, yaw: quarterTurn })),
    { id: 'mitredTrim', x: 3.6, y: 0, z: 2.4 },
  ],
  walls: [
    ...columns.slice(0, -1).map(x => ({ id: 'wall', x, y: 0, z: -2.94 })),
    { id: 'wallCorner', x: 4.2, y: 0, z: -2.94 },
    // The straight wall's finished face is local +Z. Turn it toward the corridor (-X).
    ...[-1.14, .06, 1.26].map(z => ({ id: 'wall', x: 4.2, y: 0, z, yaw: -quarterTurn })),
  ],
  ceiling: columns.flatMap(x => [-2.4, -1.2].map(z => ({
    id: 'ceiling', x, y: 3, z,
    omit: z === -1.2 && [-2.4, 0, 2.4].includes(x) ? 'PANEL_1' : null,
  }))),
};

export function instance(source, x, y, z, omit) {
  const object = source.clone(true);
  object.position.set(x, y, z);
  if (omit) object.getObjectByName(omit)?.removeFromParent();
  return object;
}

export function placeShellModule(sources, { id, x, y, z, yaw, omit }) {
  const object = instance(sources[id], x, y, z, omit);
  if (yaw !== undefined) object.rotation.y = yaw;
  return object;
}

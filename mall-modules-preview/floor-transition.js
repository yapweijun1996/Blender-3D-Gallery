import { Group } from 'three';
import { placeShellModule, shellAssetPaths } from './shell-layout.js';

export const floorTransitionPaths = {
  floor: shellAssetPaths.floor,
  floor2m: 'models/mall-floor-module-2m/exports/mall-floor-module-2m.glb',
};

// Both kits start at x = -3 and share the finished surface at y = 0.
// Their underside origins lie at different depths below it.
const rows = [
  { id: 'floor2m', count: 3, pitch: 2, y: -.10, z: -1 },
  { id: 'floor', count: 5, pitch: 1.2, y: -.03, z: .6 },
  { id: 'floor', count: 5, pitch: 1.2, y: -.03, z: 1.8 },
];

export function assembleFloorTransition(sources) {
  const group = new Group();
  group.name = 'Mixed floor grids';
  for (const { id, count, pitch, y, z } of rows) {
    for (let column = 0; column < count; column++) {
      const x = -3 + (column + .5) * pitch;
      const yaw = (column % 4) * Math.PI / 2;
      const tile = placeShellModule(sources, { id, x, y, z, yaw });
      tile.name = 'Floor_' + group.children.length;
      tile.userData.moduleId = id;
      group.add(tile);
    }
  }
  return group;
}

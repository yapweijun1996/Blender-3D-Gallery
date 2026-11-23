import { Group } from 'three';
import { placeShellModule } from './shell-layout.js';

export const cornerFloorPath = 'models/mall-floor-corner-2m/exports/mall-floor-corner-2m.glb';

export function assembleCornerTileFloor(sources) {
  const floor = new Group();
  floor.name = 'Outside floor corner';
  for (const z of [-1, 1]) {
    for (const x of [-1, 1]) {
      const id = x === 1 && z === 1 ? 'cornerFloor2m' : 'floor2m';
      const tile = placeShellModule(sources, { id, x, y: -.10, z });
      tile.name = 'Floor_' + floor.children.length;
      tile.userData.moduleId = id;
      floor.add(tile);
    }
  }
  return floor;
}

import { Group } from 'three';
import { assembleFloorTransition } from './floor-transition.js';

export const wallRunPath = 'models/mall-wall-module-2m/exports/mall-wall-module-2m.glb';

export function assembleWallRun(wallScene) {
  const group = new Group();
  group.name = 'Two metre straight wall run';
  for (const x of [-2, 0, 2]) {
    const wall = wallScene.clone(true);
    wall.name = 'Straight wall at X ' + x;
    wall.userData.moduleId = 'wall2m';
    // The back of the 150 mm wall sits on the far edge of the floor at Z = -2 m.
    wall.position.set(x, 0, -2 + .075);
    group.add(wall);
  }
  return group;
}

export function assembleWalledFloor(sources) {
  const floor = assembleFloorTransition(sources);
  return floor.add(...assembleWallRun(sources.wall2m).children);
}

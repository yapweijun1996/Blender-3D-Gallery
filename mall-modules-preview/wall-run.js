import { Group } from 'three';
import { assembleFloorTransition } from './floor-transition.js';

export const wallRunPath = 'models/mall-wall-module-2m/exports/mall-wall-module-2m.glb';
export const wallCornerPath = 'models/mall-wall-corner-2m/exports/mall-wall-corner-2m.glb';
// The backs of the 150 mm walls land at the outer floor edges.
const rear = -2 + .075;
const right = 3 - .075;

function placeWall(source, id, x, z, yaw = 0) {
  const wall = source.clone(true);
  wall.name = id + ' at ' + x + ', ' + z;
  wall.userData.moduleId = id;
  wall.position.set(x, 0, z);
  wall.rotation.y = yaw;
  return wall;
}

export function assembleWallRun(wallScene) {
  const group = new Group();
  group.name = 'Two metre straight wall run';
  for (const x of [-2, 0, 2]) {
    group.add(placeWall(wallScene, 'wall2m', x, rear));
  }
  return group;
}

export function assembleWalledFloor(sources) {
  const floor = assembleFloorTransition(sources);
  return floor.add(...assembleWallRun(sources.wall2m).children);
}

export function assembleCornerFloor(sources) {
  return assembleFloorTransition(sources).add(
    placeWall(sources.wall2m, 'wall2m', right - 3, rear),
    placeWall(sources.wallCorner2m, 'wallCorner2m', right, rear),
    placeWall(sources.wall2m, 'wall2m', right, rear + 3, -Math.PI / 2),
  );
}

export function assembleWallCeiling(ceilingScene) {
  const bank = new Group();
  bank.name = 'Ceiling over the straight wall';
  for (const x of [-2.4, -1.2, 0, 1.2, 2.4]) {
    const cassette = ceilingScene.clone(true);
    cassette.position.set(x, 2.8, -1.4);
    bank.add(cassette);
  }
  return bank;
}

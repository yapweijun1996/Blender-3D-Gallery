import { Group } from 'three';
import { batchStaticMeshes } from './batch-static.js';
import { assembleCorridor, corridorAssetPaths } from './corridor-layout.js';
import { floorTransitionPaths } from './floor-transition.js';
import { placeShellModule } from './shell-layout.js';
import { wallCornerPath, wallRunPath } from './wall-run.js';

export const roomAssetPaths = {
  floor2m: floorTransitionPaths.floor2m,
  wall2m: wallRunPath,
  wallCorner2m: wallCornerPath,
  door: corridorAssetPaths.door,
  doorHeader2m: 'models/mall-shop-door-header-2m/exports/mall-shop-door-header-2m.glb',
  ceiling: corridorAssetPaths.ceiling,
};

export const roomArrival = { x: 0, z: 4.4 };
const quarter = Math.PI / 2;
const floorCentres = [-4, -2, 0, 2, 4];
const ceilingCentres = [-2.4, -1.2, 0, 1.2, 2.4];

// The nine interior tiles sit between wall centrelines. The perimeter tiles
// support the outer halves of the walls and the open door's visitor approach.
const bodyPlacements = [
  ...floorCentres.flatMap(x => floorCentres.map(z => ({ id: 'floor2m', x, y: -.10, z }))),
  { id: 'wallCorner2m', x: 3, y: 0, z: -3 },
  { id: 'wallCorner2m', x: -3, y: 0, z: -3, yaw: quarter },
  { id: 'wallCorner2m', x: 3, y: 0, z: 3, yaw: -quarter },
  { id: 'wallCorner2m', x: -3, y: 0, z: 3, yaw: Math.PI },
  { id: 'wall2m', x: 0, y: 0, z: -3 },
  { id: 'wall2m', x: -3, y: 0, z: 0, yaw: quarter },
  { id: 'wall2m', x: 3, y: 0, z: 0, yaw: -quarter },
  // The 2.10 m frame covers 50 mm of wall on each side of the 2.00 m opening.
  // Its rear face sits on the outside wall face at z = 3.075 m.
  { id: 'door', x: 0, y: 0, z: 3.135 },
  { id: 'doorHeader2m', x: 0, y: 2.4, z: 3 },
];

export function assembleRoom(sources, furnishings = []) {
  const { group: body, poseDoors } = assembleCorridor(sources, bodyPlacements.concat(furnishings));
  body.name = 'Shop floor, walls and entrance';
  body.children.forEach((module, index) => {
    if (module.userData.moduleId === 'floor2m') module.name = 'Floor_' + index;
  });

  const roof = new Group();
  roof.name = 'Shop suspended ceiling';
  for (const x of ceilingCentres) {
    for (const z of ceilingCentres) {
      const cassette = placeShellModule(sources, { id: 'ceiling', x, y: 2.8, z });
      cassette.userData.moduleId = 'ceiling';
      roof.add(cassette);
    }
  }
  roof.visible = false;
  const group = new Group();
  group.name = 'Six metre enclosed shop';
  group.add(body, roof);
  let batched = false;
  return {
    group,
    roof,
    poseDoors,
    setRoofVisible(visible) { roof.visible = visible; },
    // Call after constructing the collision world from the original mesh roots.
    batchStatic() {
      if (batched) return;
      batchStaticMeshes(body);
      batchStaticMeshes(roof);
      batched = true;
    },
  };
}

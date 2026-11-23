import { Group } from 'three';
import { floorTransitionPaths } from './floor-transition.js';
import { placeShellModule, shellAssetPaths } from './shell-layout.js';
import { wallRunPath } from './wall-run.js';

export const ceilingInfillPaths = {
  floor2m: floorTransitionPaths.floor2m,
  wall2m: wallRunPath,
  ceiling: shellAssetPaths.ceiling,
  ceilingInfill: 'models/mall-ceiling-infill-800/exports/mall-ceiling-infill-800.glb',
};

export function assembleCeilingInfill(sources) {
  const bay = new Group();
  bay.name = '6 m corridor with a 2 m ceiling';
  const roof = new Group();
  roof.name = 'Ceiling cassettes';

  function place(parent, id, name, x, y, z, yaw = 0) {
    const part = placeShellModule(sources, { id, x, y, z, yaw });
    part.name = name;
    part.userData.moduleId = id;
    parent.add(part);
  }

  for (const [index, x] of [-2, 0, 2].entries()) {
    place(bay, 'floor2m', 'Floor_' + index, x, -.1, 0);
    // Outer faces sit on the floor edges at ±1 m. Both stone faces look into the aisle.
    place(bay, 'wall2m', 'North wall ' + index, x, 0, -.925);
    place(bay, 'wall2m', 'South wall ' + index, x, 0, .925, Math.PI);
  }
  for (const [index, x] of [-2.4, -1.2, 0, 1.2, 2.4].entries()) {
    place(roof, 'ceiling', 'Full cassette ' + index, x, 2.8, -.4);
    place(roof, 'ceilingInfill', 'Perimeter cassette ' + index, x, 2.8, .6);
  }
  bay.add(roof);
  return bay;
}

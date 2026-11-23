import { Group } from 'three';
import { placeShellModule } from './shell-layout.js';

const teeCells = [
  [0, 0],
  [-2, 0],
  [2, 0],
  [0, -2],
];
const crossCells = [...teeCells, [0, 2]];

function assemble(sources, name, cells) {
  const group = new Group();
  group.name = name;
  for (const [index, [x, z]] of cells.entries()) {
    const yaw = ((index % 4) * Math.PI) / 2;
    const tile = placeShellModule(sources, { id: 'floor2m', x, y: -0.1, z, yaw });
    tile.name = 'Floor_' + index;
    tile.userData.moduleId = 'floor2m';
    group.add(tile);
  }
  return group;
}

export function assembleTJunction(sources) {
  return assemble(sources, '2 m T-junction floor', teeCells);
}

export function assembleCrossJunction(sources) {
  return assemble(sources, '2 m cross-junction floor', crossCells);
}

import { Group } from 'three';
import { placeShellModule } from './shell-layout.js';

export const cornerFloorPath = 'models/mall-floor-corner-2m/exports/mall-floor-corner-2m.glb';

export const insideMitrePath = 'models/mall-floor-inside-mitre-2m/exports/mall-floor-inside-mitre-2m.glb';

export const floorEdgePaths = {
  edge2m: 'models/mall-floor-edge-2m/exports/mall-floor-edge-2m.glb',
  mitredEdge2m: 'models/mall-floor-edge-2m/exports/mall-floor-edge-2m-mitre.glb',
};

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

export function assembleFinishedFloorEdge(sources) {
  const floor = assembleCornerTileFloor(sources);
  floor.name = 'Finished outside floor edge';
  const placements = [
    { id: 'edge2m', x: -1, z: 2.03 },
    { id: 'edge2m', x: 2.03, z: -1, yaw: Math.PI / 2 },
    { id: 'mitredEdge2m', x: 1, z: 1 },
  ];
  // Both profiles use finished floor as their vertical datum. The mitred
  // pair uses the corner tile centre and the straight uses its cap centre.
  return addFloorEdges(sources, floor, placements);
}

function addFloorEdges(sources, floor, placements) {
  for (const placement of placements) {
    const edge = placeShellModule(sources, { ...placement, y: 0 });
    edge.userData.moduleId = placement.id;
    floor.add(edge);
  }
  return floor;
}

export function assembleInsideFloorEdge(sources) {
  const floor = new Group();
  floor.name = 'Inside floor edge';
  const centres = [[0, 0], [2, 0], [4, 0], [0, 2], [0, 4]];
  for (const [index, [x, z]] of centres.entries()) {
    const tile = placeShellModule(sources, { id: 'floor2m', x, y: -.10, z });
    tile.name = 'Floor_' + index;
    tile.userData.moduleId = 'floor2m';
    floor.add(tile);
  }
  // The inside mitre starts at the two exposed slab faces. Its square ends
  // meet the ordinary trims on the next tile in each arm of the L.
  return addFloorEdges(sources, floor, [
    { id: 'insideMitre2m', x: 1, z: 1 },
    { id: 'edge2m', x: 4, z: 1.03 },
    { id: 'edge2m', x: 1.03, z: 4, yaw: Math.PI / 2 },
  ]);
}

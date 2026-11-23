import { assembleRoom } from './room-layout.js';

export const beautyPaths = {
  pharmacyCounter: 'models/pharmacy-counter/exports/optimized.glb',
  healthShelf: 'models/medicine-health-box-set/exports/optimized.glb',
  testerBar: 'models/mall-cosmetics-tester-bar/exports/mall-cosmetics-tester-bar.glb',
};

const fixtures = [
  // Customers approach the glazed aperture from +Z. The offset leaves a route
  // around its right end to the open staff shelves behind the counter.
  { id: 'pharmacyCounter', x: -.68, y: 0, z: -.94 },
  { id: 'healthShelf', x: 2.60, y: 0, z: .65, yaw: -Math.PI / 2 },
  { id: 'testerBar', x: -2.34, y: 0, z: 1.17, yaw: Math.PI / 2 },
];

export function assemblePharmacyBeauty(sources) {
  const room = assembleRoom(sources, fixtures);
  room.group.name = 'Pharmacy and beauty shop';
  let testerBar;
  room.group.traverse(object => {
    if (object.userData.moduleId === 'testerBar') testerBar = object;
  });
  return { ...room, testerBar };
}

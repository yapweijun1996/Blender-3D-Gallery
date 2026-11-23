import { assembleRoom } from './room-layout.js';

export const bakeryPaths = {
  foodCabinet: 'models/food-display-cabinet/exports/optimized.glb',
  toastRack: 'models/kopitiam-toast-display/exports/optimized.glb',
  serviceCounter: 'models/mall-coffee-counter/exports/optimized.glb',
  servingTongs: 'models/mall-bakery-serving-tongs/exports/mall-bakery-serving-tongs.glb',
};

const counter = { id: 'serviceCounter', x: .11, y: 0, z: -.69 };
const rack = { id: 'toastRack', x: counter.x - .22, y: .97, z: counter.z - .125 };
const fixtures = [
  counter, rack, { id: 'foodCabinet', x: -1.505, y: 0, z: -.69 },
  { id: 'servingTongs', x: rack.x, y: rack.y + .254, z: rack.z + .102 },
];

export function assembleBakeryShop(sources) {
  const room = assembleRoom(sources, fixtures);
  let tongs, cabinet;
  room.group.traverse(object => {
    if (object.userData.moduleId === 'servingTongs') tongs = object;
    if (object.userData.moduleId === 'foodCabinet') cabinet = object;
  });
  // Hold the existing sliding pane at its native open endpoint. Its fixed
  // neighbour and the glazing on the customer side remain in their authored poses.
  const door = cabinet.getObjectByName('MOVABLE_RearDoor');
  door.position.x += .56;
  room.group.name = 'Bakery shop';
  return {
    ...room, tongs,
    inspection: {
      object: tongs, label: 'Inspect serving tongs',
      target: [0, .012, -.034], direction: [.20, .83, 1], radius: .210,
    },
  };
}

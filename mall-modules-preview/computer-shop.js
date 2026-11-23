import { assembleRoom } from './room-layout.js';

export const computerPaths = {
  tvTable: 'models/tv-demo-table/exports/optimized.glb',
  laptop: 'models/laptop/exports/optimized.glb',
  electronicsShelf: 'models/shelf-electronics-display/exports/optimized.glb',
  securityTether: 'models/mall-product-security-tether/exports/mall-product-security-tether.glb',
};

const demoTable = { id: 'tvTable', x: -.52, y: 0, z: .02 };
const fixtures = [
  demoTable,
  // The open notebook sits in the front bay, clear of the sign and all three TVs.
  { id: 'laptop', x: demoTable.x + .50, y: .8, z: demoTable.z + .24 },
  { id: 'electronicsShelf', x: 1.30, y: 0, z: -2.46 },
  // The tether's lower pad bonds to the laminate. Its other pad rests on the palm rest.
  { id: 'securityTether', x: demoTable.x + .77, y: .8, z: demoTable.z + .32 },
];

export function assembleComputerShop(sources) {
  const room = assembleRoom(sources, fixtures);
  room.group.name = 'Computer shop';
  let laptop;
  room.group.traverse(object => {
    if (object.userData.moduleId === 'laptop') laptop = object;
  });
  return {
    ...room, laptop,
    inspection: {
      object: laptop, label: 'Inspect demo laptop',
      target: [.060, .110, .018], direction: [.38, .68, 1], radius: .305,
    },
  };
}

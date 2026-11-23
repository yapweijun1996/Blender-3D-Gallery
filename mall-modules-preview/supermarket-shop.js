import { assembleRoom } from './room-layout.js';

export const supermarketPaths = {
  cartReturn: 'models/mall-cart-return-bay/exports/mall-cart-return-bay.glb',
  cart: 'models/shopping-cart/exports/optimized.glb',
  checkout: 'models/checkout-counter/exports/optimized.glb',
  gondola: 'models/shelf-food-aisle/exports/optimized.glb',
  securityGate: 'models/store-security-gate/exports/store-security-gate.glb',
};

const quarter = Math.PI / 2;
const bay = { id: 'cartReturn', x: -2.25, y: 0, z: 1.05, yaw: quarter };
const fixtures = [
  bay,
  ...[-.37, .37].map(offset => ({ id: 'cart', x: bay.x, y: 0, z: bay.z + offset, yaw: -quarter })),
  { id: 'checkout', x: 1.35, y: 0, z: .12, yaw: -quarter },
  { id: 'gondola', x: -1.39, y: 0, z: -1.35 },
  { id: 'securityGate', x: 0, y: 0, z: 2.35 },
];

export function assembleSupermarketShop(sources) {
  // The original gate consists of two independently installed antenna pedestals.
  // Move each complete side out 120 mm for a 1.36 m passage between its plinths.
  const securityGate = sources.securityGate.clone(true);
  const antennas = securityGate.getObjectByName('ASSET_StoreSecurityGate');
  for (const part of antennas.children) part.position.x += Math.sign(part.position.x) * .12;
  const room = assembleRoom({ ...sources, securityGate }, fixtures);
  room.group.name = 'Supermarket';
  let cartReturn;
  room.group.traverse(part => {
    if (part.userData.moduleId === 'cartReturn') cartReturn = part;
  });
  return {
    ...room,
    inspection: {
      object: cartReturn, label: 'Inspect cart return',
      target: [0, .61, .02], direction: [.26, .64, 1], radius: 1.04,
    },
  };
}

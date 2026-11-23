import { assembleRoom } from './room-layout.js';

export const furnishingPaths = {
  sofa: 'models/living-room-sofa/exports/optimized.glb',
  sideTable: 'models/bedside-table/exports/bedside-table.glb',
  oilLamp: 'models/deepavali-oil-lamp/exports/deepavali-oil-lamp.glb',
  diningTable: 'models/round-dining-table/exports/round-dining-table.glb',
  diningChair: 'models/plastic-dining-chair/exports/optimized.glb',
  orchid: 'models/orchid-planter/exports/optimized.glb',
};

const furnishings = [
  // Both seating groups face the open central aisle.
  { id: 'sofa', x: -1.20, y: 0, z: -2.16 },
  { id: 'sideTable', x: -2.54, y: 0, z: -2.16 },
  // The side cabinet's exported top sits 622.5 mm above its floor-level pivot.
  { id: 'oilLamp', x: -2.54, y: .6225, z: -2.16 },
  { id: 'diningTable', x: 1.80, y: 0, z: 0 },
  { id: 'diningChair', x: 1.80, y: 0, z: -.82 },
  { id: 'diningChair', x: 1.80, y: 0, z: .82, yaw: Math.PI },
  { id: 'orchid', x: 2.18, y: 0, z: -2.12 },
];

export function assembleHomeFurnishings(sources) {
  const room = assembleRoom(sources, furnishings);
  room.group.name = 'Home furnishings shop';
  return room;
}

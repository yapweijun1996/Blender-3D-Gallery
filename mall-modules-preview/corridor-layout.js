// The same module placements feed the orbit preview and the furnished visitor checks.
import { Group } from 'three';
import { fasciaBaseY, shopfrontAssets, shopfrontBays, shopfrontZ } from './shopfront-layout.js';
import { placeShellModule, shellAssetPaths, shellLayout } from './shell-layout.js';

export const corridorAssetPaths = {
  ...shellAssetPaths,
  ...Object.fromEntries(shopfrontAssets.map(({ id, path }) => [id, path])),
  column: 'models/mall-structural-column/exports/mall-structural-column.glb',
  railing: 'models/mall-glass-railing/exports/mall-glass-railing-2m.glb',
  light: 'models/mall-ceiling-light/exports/mall-ceiling-light-module.glb',
  bench: 'models/gjh-mall-furniture/exports/gjh-lounge-bench.glb',
  planter: 'models/gjh-mall-furniture/exports/gjh-areca-planter.glb',
  shelf: 'models/mall-essentials/exports/mall-display-shelf.glb',
  directory: 'models/mall-essentials/exports/mall-directory-kiosk.glb',
  lightbox: 'models/mall-essentials/exports/mall-advertising-lightbox.glb',
};

const shopfronts = shopfrontBays.flatMap(({ x, opening, fascia }) => {
  const bay = [
    { id: opening, x, y: 0, z: shopfrontZ },
    { id: fascia, x, y: fasciaBaseY, z: shopfrontZ },
  ];
  // The shallow shops have room for a visitor behind the doors when the display
  // shelves face out through their outer windows.
  if (opening === 'glazing' && x !== 0) bay.push({ id: 'shelf', x, y: 0, z: -2.42, yaw: Math.PI });
  return bay;
});

export const corridorLayout = [
  ...shellLayout.floor, ...shellLayout.trim,
  ...shopfronts, ...shellLayout.walls,
  ...shellLayout.ceiling.flatMap(placement => placement.omit ? [
    placement, { id: 'light', x: placement.x - .3, y: 3.008, z: placement.z + .3 },
  ] : [placement]),
  { id: 'column', x: -3.6, y: 0, z: 0 }, { id: 'column', x: 3.6, y: 0, z: 0 },
  { id: 'railing', x: -1, y: 0, z: 2.95 },
  { id: 'railing', x: 1, y: 0, z: 2.95, omit: 'MODULE_Post_Left' },
  { id: 'bench', x: 0, y: 0, z: .85, yaw: Math.PI },
  { id: 'planter', x: -3.25, y: 0, z: 1.8 }, { id: 'planter', x: 3.25, y: 0, z: 1.8 },
  { id: 'directory', x: -3.48, y: 0, z: -.72, yaw: Math.PI },
  { id: 'lightbox', x: 3.48, y: 0, z: -.72, yaw: Math.PI },
];

export const arrival = { x: 0, z: 2.08 };

export function assembleCorridor(sources, placements = corridorLayout) {
  const group = new Group();
  group.name = 'Mall corridor assembly';
  const doors = [];
  for (const [index, placement] of placements.entries()) {
    const object = placeShellModule(sources, placement);
    object.userData.moduleId = placement.id;
    if (placement.id === 'floor' || placement.id === 'cornerTile') object.name = 'Floor_' + index;
    if (placement.id === 'door') {
      const left = object.getObjectByName('HINGE_Left'), right = object.getObjectByName('HINGE_Right');
      if (!left || !right) throw new Error('Shopfront needs both editable door hinges');
      doors.push({ left, right });
    }
    group.add(object);
  }
  function poseDoors(angle) {
    const radians = angle * Math.PI / 180;
    for (const { left, right } of doors) {
      left.rotation.y = -radians;
      right.rotation.y = radians;
    }
    group.updateMatrixWorld(true);
  }
  return { group, poseDoors };
}

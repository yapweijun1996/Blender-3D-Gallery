import { Box3, Group } from 'three';
import { floorTransitionPaths } from './floor-transition.js';
import { placeShellModule } from './shell-layout.js';

export const escalatorTerminalPaths = {
  escalator: 'models/escalator/exports/optimized.glb',
  floor2m: floorTransitionPaths.floor2m,
  escalatorTransition2m: 'models/mall-escalator-floor-transition-2m/exports/mall-escalator-floor-transition-2m.glb',
};

export const passengerView = { target: [0, .83, 0], radius: 1.45, direction: [.3, 2.35, 1.6] };

export function assembleEscalatorTerminals(sources) {
  const group = new Group();
  group.name = 'Escalator and two finished floor terminals';
  const machine = placeShellModule(sources, { id: 'escalator', x: 0, y: 0, z: 0 });
  machine.userData.moduleId = 'escalator';
  group.add(machine);
  machine.updateMatrixWorld(true);

  const inspections = {};
  for (const [key, label, sign] of [['lower', 'Lower', 1], ['upper', 'Upper', -1]]) {
    // The named connectors are inboard of the actual outer deck edges.
    const deck = machine.getObjectByName('LANDING_' + label);
    const bounds = new Box3().setFromObject(deck, true);
    const terminal = new Group();
    terminal.name = label + ' terminal';
    terminal.userData.terminal = key;
    terminal.position.set(0, bounds.max.y, sign === 1 ? bounds.max.z : bounds.min.z);
    group.add(terminal);

    const profile = placeShellModule(sources, {
      id: 'escalatorTransition2m', x: 0, y: 0, z: 0, yaw: sign === 1 ? 0 : Math.PI,
    });
    profile.userData.moduleId = 'escalatorTransition2m';
    terminal.add(profile);
    // The central slab meets the 120 mm profile. Each flank tile reaches
    // back to the deck-edge plane, closing the profile's outer side face.
    for (const [role, x, outset] of [['centre', 0, 1.12], ['left', -2, 1], ['right', 2, 1]]) {
      const tile = placeShellModule(sources, { id: 'floor2m', x, y: -.10, z: sign * outset });
      tile.userData.moduleId = 'floor2m';
      tile.userData.role = role;
      terminal.add(tile);
    }

    inspections[key] = {
      object: profile,
      target: [0, -.012, .018],
      // Look outward from above the machine side so both vertical shoulder
      // faces, the bearing surface and the neighboring tiles can be seen.
      direction: [.22, 1.05, -.74],
      radius: 1.15,
    };
  }
  return { group, machine, inspections };
}

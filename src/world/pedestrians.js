import { createPeople } from "../drive/pedestrians.js";
import { disposeModels } from "../chibi-dressup/view.js";
import { pedestrianPaths, samplePath } from "./paths.js";

export { pedestrianPaths, samplePath };

// People (the dress-up chibis) walking the mapped footways around the player. Pure path helpers plus a small manager.
const PAVEMENT_Y = 0.05, SPEED = 1.4, RESEAT_DISTANCE = 260, NEAR_MIN = 20, NEAR_MAX = 150;

export async function addWorldPedestrians({ scene, signal, count = { female: 3, male: 3 } }) {
  const { people, scenes, random } = await createPeople({ scene, signal, count, seed: 31 });
  let paths = [];
  for (const person of people) { person.path = null; person.root.visible = false; }

  function seat(person, near) {
    const options = paths.filter(path => { const d = Math.hypot(path.x - near.x, path.z - near.z); return d > NEAR_MIN && d < NEAR_MAX; });
    if (!options.length) { person.path = null; person.root.visible = false; return; }
    person.path = options[Math.floor(random() * options.length)];
    person.s = random() * person.path.length;
    person.dir = random() < 0.5 ? 1 : -1;
    person.root.visible = true;
  }

  return {
    get count() { return people.length; },
    setPaths(list) { paths = list; for (const person of people) if (person.path && !paths.includes(person.path)) person.path = null; },
    update(dt, near) {
      for (const person of people) {
        if (!person.path || Math.hypot(person.path.x - near.x, person.path.z - near.z) > RESEAT_DISTANCE) { seat(person, near); if (!person.path) continue; }
        person.s += person.dir * person.speed * (SPEED / 1.5) * dt;
        if (person.s < 0 || person.s > person.path.length) { person.dir = -person.dir; person.s = Math.max(0, Math.min(person.path.length, person.s)); }
        person.rig.update(dt, { L: null, R: null });
        const at = samplePath(person.path, person.s);
        person.root.position.set(at.x, PAVEMENT_Y, at.z);
        person.root.rotation.y = Math.atan2(at.dx, at.dz) + (person.dir > 0 ? 0 : Math.PI);
      }
    },
    people,
    dispose() {
      for (const person of people) person.rig.dispose();
      disposeModels(scenes);
    },
  };
}

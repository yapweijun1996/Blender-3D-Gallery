import { clone } from "three/addons/utils/SkeletonUtils.js";
import manifestData from "../../models/chibi-dressup/manifest.json";
import { fitsBody, validateManifest } from "../chibi-dressup/config.js";
import { bindModule, createRig } from "../chibi-dressup/rig.js";
import { disposeModels, loadModels } from "../chibi-dressup/view.js";
import { sample } from "./route.js";
import { zoneAt } from "./scenery.js";

// Pedestrians are the dress-up chibis, dressed from the same manifest, walking on the pavements of built-up stretches.
const files = import.meta.glob("../../models/chibi-dressup/{bodies,modules}/**/*.glb", { eager: true, query: "?url", import: "default" });
const url = file => files[`../../models/chibi-dressup/${file}`];

// Light outfits only: pedestrians are small on screen and the download must stay modest.
const OUTFITS = {
  female: { hair: ["female-hair-bob", "female-hair-ponytail"], top: ["female-top-dress", "female-top-tshirt"], bottom: ["female-bottom-jeans"], shoes: ["female-shoes-boots", "female-shoes-sneakers"] },
  male: { hair: ["male-hair-sidepart", "male-hair-bob"], top: ["male-top-tshirt"], bottom: ["male-bottom-jeans"], shoes: ["male-shoes-boots", "male-shoes-sneakers"] },
};
const SCALE = 1.45, SPEED = 1.5, WALK_BEHIND = 140, WALK_AHEAD = 300;
const rng = seed => () => (seed = (seed * 1664525 + 1013904223) >>> 0) / 4294967296;

export async function addPedestrians({ scene, route, signal, count = { female: 3, male: 3 }, allowed = null }) {
  const ok = allowed ?? (s => { const zone = zoneAt(route, s); return !(zone === "expressway" || zone === "water" || zone === "checkpoint"); });
  const manifest = validateManifest(manifestData);
  const scenes = new Set();
  const random = rng(77);
  const bodies = Object.entries(count).filter(([, n]) => n > 0).map(([id]) => id);
  if (!bodies.length) return { update() {}, dispose() {} };
  // One shared motion bank and gesture bank; each body brings its own mesh.
  const [motion, gestures] = await loadModels([url("bodies/male/motion.glb"), url("bodies/male/gestures.glb")], signal, scenes);
  const templates = new Map();
  for (const id of bodies) {
    const [body] = await loadModels([url(`bodies/${id}/body.glb`)], signal, scenes);
    const wanted = Object.values(OUTFITS[id]).flat();
    const moduleScenes = new Map();
    for (const moduleId of wanted) {
      const spec = manifest.modules.find(module => module.id === moduleId);
      if (!spec || !fitsBody(spec, id, manifest)) continue;
      const [gltf] = await loadModels([url(spec.file)], signal, scenes);
      moduleScenes.set(moduleId, { scene: gltf.scene, slot: spec.slot, excludes: spec.excludesSlots ?? [] });
      await new Promise(resolve => setTimeout(resolve, 0)); // keep the page responsive while files are parsed
    }
    templates.set(id, { body, moduleScenes });
  }
  signal?.throwIfAborted();

  const people = [];
  for (const [id, total] of Object.entries(count)) {
    for (let i = 0; i < total; i++) {
      const { body, moduleScenes } = templates.get(id);
      const root = clone(body.scene);
      let skeleton;
      root.traverse(node => { if (node.isSkinnedMesh) { skeleton = node.skeleton; node.frustumCulled = false; } });
      // Pick one item per slot; a dress hides the bottoms.
      const chosen = {};
      for (const slot of ["hair", "top", "bottom", "shoes"]) {
        const options = OUTFITS[id][slot].filter(moduleId => moduleScenes.has(moduleId));
        if (options.length) chosen[slot] = options[Math.floor(random() * options.length)];
      }
      if (chosen.top && moduleScenes.get(chosen.top).excludes.includes("bottom")) delete chosen.bottom;
      for (const moduleId of Object.values(chosen)) {
        const copy = clone(moduleScenes.get(moduleId).scene);
        // binding rewrites the joint indices of the geometry in place, so every person needs its own copy
        copy.traverse(node => { if (node.isSkinnedMesh) node.geometry = node.geometry.clone(); });
        for (const mesh of bindModule(root, copy, skeleton)) mesh.visible = true;
      }
      const rig = createRig(root, skeleton, [motion], gestures.animations);
      rig.select("walk");
      rig.update(random() * 1.5, { L: null, R: null });
      root.scale.setScalar(SCALE);
      scene.add(root);
      people.push({ root, rig, s: 0, dir: random() < 0.5 ? 1 : -1, side: random() < 0.5 ? 1 : -1, lateral: 0.9 + random() * 2.1, speed: SPEED * (0.85 + random() * 0.3) });
    }
  }

  function place(person, around, first = false) {
    for (let tries = 0; tries < 40; tries++) {
      const s = Math.max(30, Math.min(route.length - 60, around - (first ? 40 : 0) + random() * (WALK_AHEAD + (first ? 120 : 0))));
      if (!ok(s)) continue;
      person.s = s;
      return true;
    }
    person.root.visible = false;
    return false;
  }
  let started = false;
  return {
    update(dt, playerS) {
      if (!started) { started = true; people.forEach(person => place(person, playerS, true)); }
      for (const person of people) {
        person.s += person.dir * person.speed * dt;
        if (person.s < playerS - WALK_BEHIND || person.s > playerS + WALK_AHEAD + 60) { if (!place(person, playerS + 60)) continue; }
        const visible = ok(person.s);
        person.root.visible = visible;
        if (!visible) { place(person, playerS + 60); continue; }
        person.rig.update(dt, { L: null, R: null });
        const pose = sample(route, person.s, person.side * (5.5 + person.lateral));
        person.root.position.set(pose.x, 0.3, pose.z);
        person.root.rotation.y = pose.heading + (person.dir > 0 ? 0 : Math.PI);
      }
    },
    get count() { return people.length; },
    dispose() {
      for (const person of people) person.rig.dispose();
      disposeModels(scenes);
    },
  };
}

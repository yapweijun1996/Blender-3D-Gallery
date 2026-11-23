import { languages } from "../i18n/preferences.js";

export const STORAGE_KEY = "b3g:chibi-dressup:v1";
export const MOTION_CLIPS = ["idle", "walk", "run", "wave", "jump", "nod", "dance"];
// Sitting plays sit_down, then loops sit_idle; leaving it plays stand_up first. Hold carries the cup.
export const ACTION_CLIPS = ["sit", "hold", "box", "bag", "take"];
export const CLIPS = [...MOTION_CLIPS, ...ACTION_CLIPS];
export const HANDS = ["L", "R"];
export const EXPRESSIONS = ["neutral", "happy", "surprised", "sad"];
export const GESTURES = ["fist", "open_relaxed", "point", "thumbs_up", "peace", "ok", "grip_small", "pinch", "open_wide"];

const supportedSlots = ["hair", "top", "bottom", "shoes", "hat"];
const isRecord = value => value !== null && typeof value === "object" && !Array.isArray(value);
const isSlug = value => typeof value === "string" && /^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(value);
const isModelPath = value => typeof value === "string" &&
  /^(?:[a-z0-9_-]+\/)*[a-z0-9_-]+\.glb$/.test(value);
const finite = (value, length) => Array.isArray(value) && value.length === length &&
  value.every(Number.isFinite);
const validSockets = value => value === undefined || (isRecord(value) && Object.entries(value).every(([name, item]) =>
  (["hold_item", "hold_box", "hold_bag", "jar"].includes(name) && isRecord(item) &&
    finite(item.translation, 3) && finite(item.rotation, 4) &&
    (item.scale === undefined || finite(item.scale, 3)) &&
    ["returnStop", "pickupStop"].every(key => item[key] === undefined || finite(item[key], 3))) ||
  // The chair and the shelf are placed per body: translation and scale in glTF metres.
  (["chair", "shelf"].includes(name) && isRecord(item) && finite(item.translation, 3) && finite(item.scale, 3))));
// Per-clip finger corrections: { clip: { constant: { bone: quaternion }, tracks: { rateHz, bones: { bone: [quaternion ...] } } } }.
const validLayers = value => value === undefined || (isRecord(value) && Object.entries(value).every(([clip, layer]) =>
  ["hold_box"].includes(clip) && isRecord(layer) &&
  (layer.constant === undefined || (isRecord(layer.constant) && Object.values(layer.constant).every(q => finite(q, 4)))) &&
  (layer.tracks === undefined || (isRecord(layer.tracks) && layer.tracks.rateHz > 0 && isRecord(layer.tracks.bones) &&
    Object.values(layer.tracks.bones).every(list => Array.isArray(list) && list.length > 1 && list.every(q => finite(q, 4)))))));
const isText = value => typeof value === "string" && value.trim().length > 0;

export function validateManifest(manifest) {
  if (!isRecord(manifest) || manifest.version !== 1 ||
      !Array.isArray(manifest.slots) || manifest.slots.length !== supportedSlots.length ||
      !supportedSlots.every(slot => manifest.slots.includes(slot)) ||
      !Array.isArray(manifest.modules) || !isRecord(manifest.defaults) ||
      !Array.isArray(manifest.bodies) || !manifest.bodies.length)
    throw new Error("Invalid dress-up manifest");
  const bodyIds = new Set();
  for (const body of manifest.bodies) {
    if (!isRecord(body) || !isSlug(body.id) || bodyIds.has(body.id) ||
        !isRecord(body.label) || !Object.keys(languages).every(locale => isText(body.label[locale])) ||
        !isModelPath(body.body) || !isModelPath(body.gestures) || !validSockets(body.sockets) || !validLayers(body.layers) ||
        !Array.isArray(body.motion) || !body.motion.length || !body.motion.every(isModelPath))
      throw new Error("Invalid dress-up body");
    bodyIds.add(body.id);
  }
  const ids = new Set();
  const files = new Set();
  for (const module of manifest.modules) {
    if (!isRecord(module) || !isSlug(module.id) || ids.has(module.id) ||
        !manifest.slots.includes(module.slot) || typeof module.file !== "string" ||
        !/^modules\/[a-z0-9]+(?:[-_][a-z0-9]+)*\.glb$/.test(module.file) || files.has(module.file) ||
        !isRecord(module.label) || !Object.keys(languages).every(locale => isText(module.label[locale])) ||
        (module.excludesSlots !== undefined && (!Array.isArray(module.excludesSlots) ||
          module.excludesSlots.some(slot => !manifest.slots.includes(slot) || slot === module.slot))) ||
        (module.bodyIds !== undefined && (!Array.isArray(module.bodyIds) || !module.bodyIds.length ||
          module.bodyIds.some(id => !bodyIds.has(id)))) ||
        (module.family !== undefined && !isSlug(module.family)) ||
        !["verified", "pending"].includes(module.status) ||
        !Number.isSafeInteger(module.bytes) || module.bytes <= 0 ||
        typeof module.sha256 !== "string" || !/^[a-f0-9]{64}$/.test(module.sha256))
      throw new Error("Invalid dress-up module");
    ids.add(module.id);
    files.add(module.file);
  }
  for (const [slot, id] of Object.entries(manifest.defaults)) {
    if (slot === "body") {
      if (!bodyIds.has(id)) throw new Error("Invalid dress-up default");
      continue;
    }
    if (!manifest.slots.includes(slot) ||
        (id !== null && !manifest.modules.some(module => module.slot === slot && module.id === id)))
      throw new Error("Invalid dress-up default");
  }
  return manifest;
}

/** A module fits the bodies it lists; without a list it belongs to the first body. */
export const fitsBody = (module, bodyId, manifest) => (module.bodyIds ?? [manifest.bodies[0].id]).includes(bodyId);
export const moduleFamily = module => module.family ?? module.id;
export const selectableModulesForBody = (bodyId, manifest) => manifest.modules.filter(module =>
  module.status === "verified" && fitsBody(module, bodyId, manifest));

/** Carry the chosen modules over to another body by family (hair-bob, top-tshirt ...). */
export function modulesForBody(modules, bodyId, manifest) {
  const selectable = selectableModulesForBody(bodyId, manifest);
  return Object.fromEntries(manifest.slots.map(slot => {
    const current = manifest.modules.find(module => module.status === "verified" && module.id === modules[slot]);
    const match = current && selectable.find(module => module.slot === slot &&
      moduleFamily(module) === moduleFamily(current));
    return [slot, match?.id ?? null];
  }));
}

export function normalizeConfig(value, manifest) {
  const defaultBody = manifest.defaults.body ?? manifest.bodies[0].id;
  const body = manifest.bodies.some(item => item.id === value?.body) ? value.body : defaultBody;
  const selectable = selectableModulesForBody(body, manifest);
  const modules = Object.fromEntries(manifest.slots.map(slot => {
    const fallbackId = Object.hasOwn(manifest.defaults, slot) ? manifest.defaults[slot] : null;
    const fallback = selectable.some(module => module.id === fallbackId && module.slot === slot)
      ? fallbackId : null;
    if (!isRecord(value?.modules) || !Object.hasOwn(value.modules, slot)) return [slot, fallback];
    const id = value.modules[slot];
    const valid = selectable.some(module => module.id === id && module.slot === slot);
    return [slot, id === null || valid ? id : fallback];
  }));
  const hands = Object.fromEntries(HANDS.map(side => {
    const gesture = value?.hands?.[side];
    return [side, GESTURES.includes(gesture) ? gesture : null];
  }));
  return {
    body, modules, animation: CLIPS.includes(value?.animation) ? value.animation : "idle", hands,
    expression: EXPRESSIONS.includes(value?.expression) ? value.expression : "neutral",
  };
}

export function loadConfig(manifest, storage) {
  try {
    return normalizeConfig(JSON.parse((storage ?? globalThis.localStorage).getItem(STORAGE_KEY)), manifest);
  } catch {
    return normalizeConfig(null, manifest);
  }
}

export function saveConfig(value, manifest, storage) {
  try {
    (storage ?? globalThis.localStorage).setItem(STORAGE_KEY, JSON.stringify(normalizeConfig(value, manifest)));
  } catch {
    // The live configuration remains usable if storage is unavailable.
  }
}

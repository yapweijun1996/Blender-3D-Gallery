import { languages } from "../i18n/preferences.js";

export const STORAGE_KEY = "b3g:chibi-dressup:v1";
export const CLIPS = ["idle", "walk", "run", "wave", "jump", "nod", "dance"];
export const HANDS = ["L", "R"];
export const GESTURES = ["fist", "open_relaxed", "point", "thumbs_up", "peace", "ok", "grip_small", "pinch", "open_wide"];

const supportedSlots = ["hair", "top", "bottom", "shoes", "hat"];
const isRecord = value => value !== null && typeof value === "object" && !Array.isArray(value);
const isSlug = value => typeof value === "string" && /^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(value);
const isText = value => typeof value === "string" && value.trim().length > 0;

export function validateManifest(manifest) {
  if (!isRecord(manifest) || manifest.version !== 1 ||
      !Array.isArray(manifest.slots) || manifest.slots.length !== supportedSlots.length ||
      !supportedSlots.every(slot => manifest.slots.includes(slot)) ||
      !Array.isArray(manifest.modules) || !isRecord(manifest.defaults))
    throw new Error("Invalid dress-up manifest");
  const ids = new Set();
  const files = new Set();
  for (const module of manifest.modules) {
    if (!isRecord(module) || !isSlug(module.id) || ids.has(module.id) ||
        !manifest.slots.includes(module.slot) || typeof module.file !== "string" ||
        !/^modules\/[a-z0-9]+(?:[-_][a-z0-9]+)*\.glb$/.test(module.file) || files.has(module.file) ||
        !isRecord(module.label) || !Object.keys(languages).every(locale => isText(module.label[locale])) ||
        !["verified", "pending"].includes(module.status) ||
        !Number.isSafeInteger(module.bytes) || module.bytes <= 0 ||
        typeof module.sha256 !== "string" || !/^[a-f0-9]{64}$/.test(module.sha256))
      throw new Error("Invalid dress-up module");
    ids.add(module.id);
    files.add(module.file);
  }
  for (const [slot, id] of Object.entries(manifest.defaults)) {
    if (!manifest.slots.includes(slot) ||
        (id !== null && !manifest.modules.some(module => module.slot === slot && module.id === id)))
      throw new Error("Invalid dress-up default");
  }
  return manifest;
}

export function normalizeConfig(value, manifest) {
  const modules = Object.fromEntries(manifest.slots.map(slot => {
    const fallback = Object.hasOwn(manifest.defaults, slot) ? manifest.defaults[slot] : null;
    if (!isRecord(value?.modules) || !Object.hasOwn(value.modules, slot)) return [slot, fallback];
    const id = value.modules[slot];
    return [slot, id === null || manifest.modules.some(module => module.id === id && module.slot === slot) ? id : fallback];
  }));
  const hands = Object.fromEntries(HANDS.map(side => {
    const gesture = value?.hands?.[side];
    return [side, GESTURES.includes(gesture) ? gesture : null];
  }));
  return { modules, animation: CLIPS.includes(value?.animation) ? value.animation : "idle", hands };
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

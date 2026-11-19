import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import test from "node:test";
import { messages } from "../src/i18n/index.js";
import { CLIPS, EXPRESSIONS, GESTURES, HANDS, STORAGE_KEY, fitsBody, loadConfig, modulesForBody, saveConfig, validateManifest } from "../src/chibi-dressup/config.js";

const directory = new URL("../models/chibi-dressup/", import.meta.url);
const manifest = JSON.parse(readFileSync(new URL("manifest.json", directory), "utf8"));

test("dress-up manifest describes real module bytes and localized controls", () => {
  assert.equal(validateManifest(manifest), manifest);
  assert.deepEqual(manifest.slots, ["hair", "top", "bottom", "shoes", "hat"]);
  assert.ok(manifest.modules.length >= 2);
  for (const { file, bytes, sha256 } of manifest.modules) {
    const data = readFileSync(new URL(file, directory));
    assert.equal(data.toString("ascii", 0, 4), "glTF");
    assert.equal(data.length, bytes, file);
    assert.equal(createHash("sha256").update(data).digest("hex"), sha256, file);
  }
  const keys = [
    "dressup.expression", ...EXPRESSIONS.map(name => `dressup.expression.${name}`),
    "demo.chibi-dressup.title", "demo.chibi-dressup.description", "dressup.loading",
    "dressup.wardrobe", "dressup.hands", "dressup.gesture.none", "motion.stage",
    ...manifest.slots.map(name => `dressup.slot.${name}`),
    ...HANDS.map(name => `dressup.hand.${name}`),
    ...GESTURES.map(name => `dressup.gesture.${name}`),
    ...CLIPS.map(name => `clip.${name}`),
  ];
  for (const [locale, table] of Object.entries(messages)) {
    for (const key of keys) assert.ok(table[key]?.trim(), `${locale}: ${key}`);
  }
});

test("dress-up manifest rejects missing labels, unsafe files and foreign defaults", () => {
  for (const change of [
    value => { value.version = 2; },
    value => { value.slots[0] = "hat"; },
    value => { value.modules.push(value.modules[0]); },
    value => { value.modules[0].file = "modules/../body.glb"; },
    value => { value.modules[0].label.ms = " "; },
    value => { value.modules[0].status = "unknown"; },
    value => { value.modules[0].bytes = "1"; },
    value => { value.modules[0].sha256 = "abc"; },
    value => { value.defaults.top = value.defaults.hair; },
    value => { value.bodies = []; },
    value => { value.bodies[0].motion = ["../x.glb"]; },
    value => { value.modules[0].bodyIds = ["unknown"]; },
    value => { value.defaults.body = "unknown"; },
    value => { value.modules.find(module => module.id === "top-dress").excludesSlots = ["top"]; },
    value => { value.modules.find(module => module.id === "top-dress").excludesSlots = ["unknown"]; },
  ]) {
    const invalid = structuredClone(manifest);
    change(invalid);
    assert.throws(() => validateManifest(invalid), /Invalid dress-up/);
  }
});

test("dress-up config round trips with independent hands and hidden slots", () => {
  const data = new Map();
  const storage = { getItem: key => data.get(key) ?? null, setItem: (key, value) => data.set(key, value) };
  const config = loadConfig(manifest, storage);
  assert.deepEqual(config.modules, {
    hair: "hair-bob", top: null, bottom: null, shoes: null, hat: null,
  });
  assert.equal(config.expression, "neutral");
  assert.equal(config.body, "neutral");
  config.modules.hair = null;
  config.animation = "wave";
  config.hands = { L: "peace", R: "fist" };
  config.expression = "sad";
  saveConfig(config, manifest, storage);
  assert.deepEqual(JSON.parse(data.get(STORAGE_KEY)), config);
  assert.deepEqual(loadConfig(manifest, storage), config);
  assert.deepEqual(loadConfig(manifest, { getItem: () => "{" }).hands, { L: null, R: null });
});

test("stale config preserves valid choices and blocked storage leaves a usable default", () => {
  const old = {
    modules: { hair: "removed", top: null, bottom: "hair-bob", shoes: "removed-shoes", unknown: "item" },
    animation: "unknown", hands: { L: "point", R: "unknown" },
  };
  assert.deepEqual(loadConfig(manifest, { getItem: () => JSON.stringify(old) }), {
    modules: { hair: "hair-bob", top: null, bottom: null, shoes: null, hat: null },
    animation: "idle", hands: { L: "point", R: null }, expression: "neutral", body: "neutral",
  });
  const blocked = () => { throw new Error("Storage blocked"); };
  assert.equal(loadConfig(manifest, { getItem: blocked }).animation, "idle");
  assert.doesNotThrow(() => saveConfig(old, manifest, { setItem: blocked }));
});

test("bodies decide which modules fit and families carry choices across bodies", () => {
  const two = structuredClone(manifest);
  two.bodies = two.bodies.slice(0, 1);
  two.modules = two.modules.filter(module => fitsBody(module, two.bodies[0].id, two));
  two.bodies.push({ ...two.bodies[0], id: "spare", label: { ...two.bodies[0].label }, body: "bodies/spare/body.glb",
    motion: ["bodies/spare/motion.glb"], gestures: "bodies/spare/gestures.glb" });
  const source = two.modules.find(module => module.id === "hair-bob");
  two.modules.push({ ...source, id: "spare-hair-bob", family: "hair-bob", bodyIds: ["spare"], file: "modules/spare-hair-bob.glb" });
  assert.equal(validateManifest(two), two);
  assert.ok(fitsBody(source, "neutral", two) && !fitsBody(source, "spare", two));
  assert.deepEqual(modulesForBody({ hair: "hair-bob", top: "top-tshirt", bottom: null, shoes: null, hat: null }, "spare", two),
    { hair: "spare-hair-bob", top: null, bottom: null, shoes: null, hat: null });
  const withSockets = structuredClone(two);
  withSockets.bodies[1].sockets = { hold_box: { translation: [0, 0, 0], rotation: [0, 0, 0, 1] }, chair: { translation: [0, 0, -0.028], scale: [1, 0.96, 1] } };
  assert.equal(validateManifest(withSockets), withSockets);
  withSockets.bodies[1].sockets.chair.scale = [1, 1];
  assert.throws(() => validateManifest(withSockets), /Invalid dress-up body/);
  withSockets.bodies[1].sockets.chair.scale = [1, 0.96, 1];
  withSockets.bodies[1].layers = { hold_box: {
    constant: { "mixamorig:RightHandThumb1": [0, 0, 0, 1] },
    tracks: { rateHz: 48, bones: { "mixamorig:LeftHandIndex1": [[0, 0, 0, 1], [0, 0, 0, 1]] } },
  } };
  assert.equal(validateManifest(withSockets), withSockets);
  for (const bad of [{ walk: {} }, { hold_box: { constant: { a: [0, 0, 1] } } },
    { hold_box: { tracks: { rateHz: 0, bones: {} } } }, { hold_box: { tracks: { rateHz: 48, bones: { a: [[0, 0, 0, 1]] } } } }]) {
    withSockets.bodies[1].layers = bad;
    assert.throws(() => validateManifest(withSockets), /Invalid dress-up body/);
  }
  const stored = { body: "spare", modules: { hair: "hair-bob" }, animation: "walk" };
  const loaded = loadConfig(two, { getItem: () => JSON.stringify(stored) });
  assert.equal(loaded.body, "spare");
  assert.equal(loaded.modules.hair, null, "a neutral module is not valid on another body");
  assert.equal(loadConfig(two, { getItem: () => JSON.stringify({ body: "unknown" }) }).body, "neutral");
});

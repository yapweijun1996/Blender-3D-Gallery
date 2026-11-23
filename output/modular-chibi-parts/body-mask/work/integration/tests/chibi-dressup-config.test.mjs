import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import test from "node:test";
import { Texture } from "three";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { messages } from "../src/i18n/index.js";
import { BODY_REGIONS, CLIPS, GESTURES, HANDS, STORAGE_KEY, loadConfig, saveConfig, validateManifest } from "../src/chibi-dressup/config.js";

import { bindModule, createRig } from "../src/chibi-dressup/rig.js";
import { applyBodyMask, getBodyRegions } from "../src/chibi-dressup/view.js";

const directory = new URL("../models/chibi-dressup/", import.meta.url);
const manifest = JSON.parse(readFileSync(new URL("manifest.json", directory), "utf8"));

test("dress-up manifest describes real module bytes and localized controls", () => {
  assert.equal(validateManifest(manifest), manifest);
  assert.deepEqual(manifest.slots, ["hair", "top", "bottom", "shoes", "hat"]);
  assert.ok(manifest.modules.length >= 3);
  for (const { file, bytes, sha256 } of manifest.modules) {
    const data = readFileSync(new URL(file, directory));
    assert.equal(data.toString("ascii", 0, 4), "glTF");
    assert.equal(data.length, bytes, file);
    assert.equal(createHash("sha256").update(data).digest("hex"), sha256, file);
  }
  const keys = [
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
    value => { value.modules[0].hides = "torso"; },
    value => { value.modules[0].hides = null; },
    value => { value.modules[0].hides = ["neck", "neck"]; },
    value => { value.modules[0].hides = ["left-forearm"]; },
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
    hair: "hair-bob", top: "top-tshirt", bottom: null, shoes: "shoes-sneakers", hat: null,
  });
  config.modules.hair = null;
  config.animation = "wave";
  config.hands = { L: "peace", R: "fist" };
  saveConfig(config, manifest, storage);
  assert.deepEqual(JSON.parse(data.get(STORAGE_KEY)), config);
  assert.deepEqual(loadConfig(manifest, storage), config);
  assert.deepEqual(loadConfig(manifest, { getItem: () => "{" }).hands, { L: null, R: null });
});

test("stale config preserves valid choices and blocked storage leaves a usable default", () => {
  const old = {
    modules: { hair: "removed", top: null, bottom: "hair-bob", shoes: "shoes-sneakers", unknown: "item" },
    animation: "unknown", hands: { L: "point", R: "unknown" },
  };
  assert.deepEqual(loadConfig(manifest, { getItem: () => JSON.stringify(old) }), {
    modules: { hair: "hair-bob", top: null, bottom: null, shoes: "shoes-sneakers", hat: null },
    animation: "idle", hands: { L: "point", R: null },
  });
  const blocked = () => { throw new Error("Storage blocked"); };
  assert.equal(loadConfig(manifest, { getItem: blocked }).animation, "idle");
  assert.doesNotThrow(() => saveConfig(old, manifest, { setItem: blocked }));
});

test("dress-up region names and skin in the body GLB match the manifest contract", () => {
  const data = readFileSync(new URL("base_body_regions.glb", directory));
  const gltf = JSON.parse(data.toString("utf8", 20, 20 + data.readUInt32LE(12)));
  assert.equal(gltf.skins.length, 1);
  assert.equal(gltf.skins[0].joints.length, 65);
  const nodes = gltf.nodes.filter(node => node.mesh !== undefined);
  assert.deepEqual(nodes.map(node => node.name).sort(), [...BODY_REGIONS].sort());
  assert.ok(nodes.every(node => node.skin === 0 && gltf.meshes[node.mesh].name === node.name));
});

test("body masks follow equipped modules and restore only after the last reference is removed", () => {
  const regions = new Map(BODY_REGIONS.map(name => [name, { visible: true }]));
  const top = manifest.modules.find(module => module.id === "top-tshirt");
  const hoodie = manifest.modules.find(module => module.id === "top-hoodie");
  const bottom = { hides: ["torso", "pelvis"] };
  const hair = manifest.modules.find(module => module.id === "hair-bob");
  const visible = region => regions.get(region).visible;
  applyBodyMask(regions, [top, bottom, hair]);
  assert.equal(visible("torso"), false);
  assert.equal(visible("upper_arm_L"), false);
  assert.equal(visible("pelvis"), false);
  assert.equal(visible("forearm_L"), true);
  applyBodyMask(regions, [hoodie, bottom, hair]);
  assert.equal(visible("forearm_L"), false);
  assert.equal(visible("hand_L"), true);
  applyBodyMask(regions, [bottom, hair]);
  assert.equal(visible("torso"), false);
  assert.equal(visible("forearm_L"), true);
  assert.equal(visible("upper_arm_L"), true);
  applyBodyMask(regions, [hair]);
  assert.ok([...regions.values()].every(mesh => mesh.visible));
});

test("real region GLB preserves the original faces and supports clips and hand poses", async () => {
  // The embedded image is validated separately. Node has no browser image decoder.
  const loader = new GLTFLoader().register(() => ({
    name: "node-test-textures",
    loadTexture: () => Promise.resolve(new Texture()),
  }));
  const load = name => loader.parseAsync(Uint8Array.from(readFileSync(new URL(name, directory))).buffer, "");
  const [original, body, motion, gestures, ...garments] = await Promise.all([
    load("base_body.glb"), load("base_body_regions.glb"), load("motion-clips.glb"), load("hand_gestures.glb"),
    ...manifest.modules.map(module => load(module.file)),
  ]);
  const { regions, skeleton } = getBodyRegions(body.scene);
  const originalMesh = original.scene.getObjectByName("Base_Body");
  assert.deepEqual(skeleton.bones.map(bone => bone.name), originalMesh.skeleton.bones.map(bone => bone.name));
  assert.deepEqual(skeleton.boneInverses, originalMesh.skeleton.boneInverses);

  function faceKeys(meshes) {
    const faces = [];
    for (const { geometry } of meshes) {
      const attributes = ["position", "normal", "uv", "skinIndex", "skinWeight"].map(name => geometry.getAttribute(name));
      for (let corner = 0; corner < geometry.index.count; corner += 3) {
        const triangle = [];
        for (let index = corner; index < corner + 3; index++) {
          const vertex = geometry.index.getX(index);
          for (const { array, itemSize } of attributes)
            triangle.push(...array.subarray(vertex * itemSize, (vertex + 1) * itemSize));
        }
        faces.push(JSON.stringify(triangle));
      }
    }
    return faces.sort();
  }

  assert.deepEqual(faceKeys(regions.values()), faceKeys([originalMesh]));
  for (const garment of garments) {
    assert.ok(bindModule(body.scene, garment.scene, skeleton).every(mesh => mesh.skeleton === skeleton));
  }
  const rig = createRig(body.scene, skeleton, motion, gestures.animations);
  const finger = "mixamorigLeftHandIndex1";
  const fingerScale = skeleton.bones.find(bone => bone.name === finger).scale;
  const stack = gestures.animations.find(action => action.name === "hand_fist_L");
  const track = stack.tracks.find(candidate => candidate.name === finger + ".quaternion");
  const scaleTrack = stack.tracks.find(candidate => candidate.name === finger + ".scale");
  for (const clip of CLIPS) {
    rig.select(clip);
    rig.update(0.125, { L: null, R: null });
    const before = rig.inspect();
    assert.equal(before.clip, clip);
    assert.ok(before.time > 0);
    const baselineScale = fingerScale.toArray();
    rig.update(0, { L: "fist", R: null });
    const rotation = rig.inspect().joints.find(joint => joint.name === finger).rotation;
    const dot = rotation.reduce((sum, value, index) => sum + value * track.values[index], 0);
    assert.ok(Math.abs(Math.abs(dot) - 1) < 1e-6);
    assert.deepEqual(fingerScale.toArray(), Array.from(scaleTrack.values));
    rig.update(0, { L: "open_wide", R: "point" });
    assert.deepEqual(fingerScale.toArray(), baselineScale);
    rig.update(0, { L: null, R: null });
    assert.deepEqual(rig.inspect().joints, before.joints);
    assert.deepEqual(fingerScale.toArray(), baselineScale);
  }
  rig.dispose();
});

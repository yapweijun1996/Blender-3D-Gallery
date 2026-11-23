import assert from "node:assert/strict";
import { readdir, readFile, writeFile } from "node:fs/promises";
import { AnimationMixer, Texture } from "../../../../node_modules/three/build/three.module.js";
import { GLTFLoader } from "../../../../node_modules/three/examples/jsm/loaders/GLTFLoader.js";
import { bindModule, createRig } from "../../../../src/chibi-dressup/rig.js";

const loader = new GLTFLoader();
// Blender verifies the packed maps. This headless test exercises the real
// demo rig, GLTFLoader animation tracks and skin remapper without a DOM.
loader.register(() => ({ name: "Offline texture placeholders", loadTexture: () => Promise.resolve(new Texture()) }));
async function load(file) {
  const bytes = await readFile(new URL(file, import.meta.url));
  return loader.parseAsync(bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength), "");
}
function skeleton(scene) {
  let found;
  scene.traverse(node => {
    if (node.isSkinnedMesh) found = node.skeleton;
  });
  assert(found && found.bones.length === 65);
  return found;
}
const body = await load("body_male.glb");
const motion = await load("motion_male.glb");
const gestures = await load("hand_gestures_male.glb");
const skel = skeleton(body.scene);
const rig = createRig(body.scene, skel, motion, gestures.animations, motion, motion);
const modules = {};
for (const file of (await readdir(new URL(".", import.meta.url))).filter(f => /^male-.*\.glb$/.test(f))) {
  const module = await load(file);
  modules[file] = bindModule(body.scene, module.scene, skel).length;
}
const mixer = new AnimationMixer(body.scene);
for (const clip of motion.animations) {
  assert(clip.duration > 0 && clip.tracks.length >= 65, clip.name);
  mixer.clipAction(clip).play().reset();
  mixer.update(clip.duration / 2);
  assert(skel.bones.every(b => [...b.quaternion.toArray(), ...b.position.toArray()].every(Number.isFinite)), clip.name);
  mixer.stopAllAction();
}
const report = {
  bodyJoints: skel.bones.length, clipNames: motion.animations.map(clip => clip.name),
  gestureNames: gestures.animations.map(clip => clip.name), moduleMeshes: modules,
  createRigAcceptedAllInputs: Boolean(rig),
  limitations: "Image decoding is validated in Blender. The demo legacy in-place branch discards non-Hips translations and animated scales, so the smoke test uses complete tracks for clip playback."
};
await writeFile(new URL("qa/demo_runtime_smoke.json", import.meta.url), JSON.stringify(report, null, 2) + "\n");
console.log(report);

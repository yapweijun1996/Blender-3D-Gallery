import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { AnimationMixer, Vector3 } from "three";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";

// Node has no image decoder. Exercise the exported joints and weights without materials.
const bytes = readFileSync(new URL("./visitor.glb", import.meta.url));
const jsonSize = bytes.readUInt32LE(12);
const data = JSON.parse(bytes.subarray(20, 20 + jsonSize));
for (const mesh of data.meshes)
  for (const primitive of mesh.primitives) delete primitive.material;
data.buffers[0].uri = "data:application/octet-stream;base64," + bytes.subarray(28 + jsonSize).toString("base64");
globalThis.ProgressEvent ??= class extends Event {};
const gltf = await new GLTFLoader().parseAsync(JSON.stringify(data), "");
assert.deepEqual(gltf.animations.map(clip => clip.name).sort(), ["Idle", "Nod", "Walk", "Wave"]);
let mesh;
gltf.scene.traverse(object => { if (object.isSkinnedMesh) mesh = object; });
const mixer = new AnimationMixer(gltf.scene);
const vertex = new Vector3();
let maxContactError = 0;
mixer.clipAction(gltf.animations.find(clip => clip.name === "Walk")).play();
for (let sample = 0; sample < 180; sample++) {
  mixer.setTime(gltf.animations.find(clip => clip.name === "Walk").duration * sample / 180);
  gltf.scene.updateMatrixWorld(true);
  let lowest = Infinity;
  for (let i = 0; i < mesh.geometry.attributes.position.count; i++)
    lowest = Math.min(lowest, mesh.localToWorld(mesh.getVertexPosition(i, vertex)).y);
  maxContactError = Math.max(maxContactError, Math.abs(lowest));
}
console.log("Maximum sampled walk contact error (metres):", maxContactError);
assert.ok(maxContactError < .004, "At least one sole should stay within 4 mm of the floor");

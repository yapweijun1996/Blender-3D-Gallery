import { AnimationClip, AnimationMixer, LoopOnce, LoopRepeat, PropertyBinding, Quaternion } from "three";
import { GESTURES, HANDS, MOTION_CLIPS } from "./config.js";

const ACTION_SOURCE_CLIPS = ["sit_down", "sit_idle", "stand_up", "hold_item", "hold_box", "hold_bag", "take_item"];
const BLEND_SECONDS = 0.3;
const ONE_SHOT = new Set(["sit_down", "stand_up"]);

const hips = "mixamorigHips";
const digits = {
  L: /^mixamorigLeftHand(?:Thumb|Index|Middle|Ring|Pinky)[1-4]$/,
  R: /^mixamorigRightHand(?:Thumb|Index|Middle|Ring|Pinky)[1-4]$/,
};
const targetTrack = (bone, property) => `${bone.uuid}.${property}`;

function retargetMotion(source, bones, names, inPlace) {
  const rest = new Map();
  source.scene.updateMatrixWorld(true);
  for (const bone of bones) {
    const original = source.scene.getObjectByName(bone.name);
    if (!original) throw new Error(`Missing motion joint ${bone.name}`);
    const sourceToTarget = bone.getWorldQuaternion(new Quaternion()).invert()
      .multiply(original.getWorldQuaternion(new Quaternion()));
    rest.set(bone.name, {
      bone,
      sourceToTargetInverse: sourceToTarget.clone().invert(),
      toTargetLocal: bone.quaternion.clone().multiply(sourceToTarget).multiply(original.quaternion.clone().invert()),
      sourceHeight: original.position.y,
      sourcePosition: original.position.clone(),
    });
  }
  const quaternion = new Quaternion();
  return new Map(names.map(name => {
    const clip = AnimationClip.findByName(source.animations, name);
    if (!clip || !(clip.duration > 0)) throw new Error(`Missing motion clip ${name}`);
    const tracks = [];
    for (const track of clip.tracks) {
      const { nodeName, propertyName } = PropertyBinding.parseTrackName(track.name);
      const joint = rest.get(nodeName);
      if (!joint) continue;
      if (propertyName === "quaternion") {
        const rotation = track.clone();
        rotation.name = targetTrack(joint.bone, "quaternion");
        for (let index = 0; index < rotation.values.length; index += 4) {
          // Transfer the rest-relative rotation through the two bone bases.
          quaternion.fromArray(rotation.values, index).premultiply(joint.toTargetLocal)
            .multiply(joint.sourceToTargetInverse).normalize().toArray(rotation.values, index);
        }
        tracks.push(rotation);
      } else if (!inPlace && propertyName === "position") {
        // Authored actions move bones for real (hips back and down onto a chair, shins when seated).
        const position = track.clone();
        position.name = targetTrack(joint.bone, "position");
        for (let index = 0; index < position.values.length; index += 3) {
          position.values[index] += joint.bone.position.x - joint.sourcePosition.x;
          position.values[index + 1] += joint.bone.position.y - joint.sourcePosition.y;
          position.values[index + 2] += joint.bone.position.z - joint.sourcePosition.z;
        }
        tracks.push(position);
      } else if (!inPlace && propertyName === "scale") {
        const scale = track.clone();
        scale.name = targetTrack(joint.bone, "scale");
        tracks.push(scale);
      } else if (inPlace && nodeName === hips && propertyName === "position") {
        const position = track.clone();
        position.name = targetTrack(joint.bone, "position");
        const { x, y, z } = joint.bone.position;
        for (let index = 0; index < position.values.length; index += 3) {
          // Keep locomotion in place, with the original jump and vertical bob.
          position.values[index] = x;
          position.values[index + 1] += y - joint.sourceHeight;
          position.values[index + 2] = z;
        }
        tracks.push(position);
      }
    }
    if (!tracks.length) throw new Error(`Motion clip has no mapped tracks: ${name}`);
    return [name, new AnimationClip(name, clip.duration, tracks)];
  }));
}

function readGestures(clips, bones) {
  const byName = new Map(bones.map(bone => [bone.name, bone]));
  const poses = new Map();
  for (const side of HANDS) {
    const expected = bones.filter(bone => digits[side].test(bone.name)).length;
    for (const gesture of GESTURES) {
      const name = `hand_${gesture}_${side}`;
      const clip = AnimationClip.findByName(clips, name);
      if (!clip || clip.tracks.length !== expected || expected === 0) throw new Error(`Missing hand pose ${name}`);
      const seen = new Set();
      poses.set(name, clip.tracks.map(track => {
        const { nodeName, propertyName } = PropertyBinding.parseTrackName(track.name);
        const bone = byName.get(nodeName);
        if (!bone || !digits[side].test(nodeName) || seen.has(bone) ||
            propertyName !== "quaternion" || track.times.length !== 1)
          throw new Error(`Invalid hand pose track: ${track.name}`);
        seen.add(bone);
        return { bone, pose: new Quaternion().fromArray(track.values).normalize(), baseline: new Quaternion() };
      }));
    }
  }
  return poses;
}

export function bindModule(model, scene, bodySkeleton) {
  const indexByName = new Map(bodySkeleton.bones.map((bone, index) => [bone.name, index]));
  const meshes = [];
  scene.updateMatrixWorld(true);
  scene.traverse(node => { if (node.isSkinnedMesh) meshes.push(node); });
  if (!meshes.length) throw new Error("Module has no skinned mesh");
  const mappings = meshes.map(mesh => {
    const boneIndices = mesh.skeleton.bones.map(bone => indexByName.get(bone.name));
    if (boneIndices.length !== bodySkeleton.bones.length ||
        boneIndices.includes(undefined) || new Set(boneIndices).size !== boneIndices.length)
      throw new Error(`Module joints do not match body: ${mesh.name}`);
    return boneIndices;
  });
  const sourceSkeletons = new Set(meshes.map(mesh => mesh.skeleton));
  const remapped = new Set();
  for (const [index, mesh] of meshes.entries()) {
    const mapping = mappings[index];
    const joints = mesh.geometry.getAttribute("skinIndex");
    if (!remapped.has(joints)) {
      for (let vertex = 0; vertex < joints.count; vertex++) {
        joints.setXYZW(vertex, mapping[joints.getX(vertex)], mapping[joints.getY(vertex)],
          mapping[joints.getZ(vertex)], mapping[joints.getW(vertex)]);
      }
      joints.needsUpdate = true;
      remapped.add(joints);
    }
    model.attach(mesh);
    mesh.bind(bodySkeleton, mesh.bindMatrix.clone());
    mesh.frustumCulled = false;
    mesh.visible = false;
  }
  for (const skeleton of sourceSkeletons) skeleton.dispose();
  return meshes;
}

/**
 * `sources` are the loaded motion GLBs of the chosen body (one file with all fourteen clips or several).
 * Shared locomotion clips stay in place; authored actions keep their own hip, leg and scale tracks.
 * `layers` holds measured finger corrections for one clip of this body (see validLayers in config.js):
 * each is multiplied onto the animated joint rotation, either fixed or slerped along a looping track.
 */
export function createRig(model, skeleton, sources, handClips, layers = {}) {
  model.updateMatrixWorld(true);
  const bones = skeleton.bones;
  const rest = bones.map(bone => bone.quaternion.toArray());
  const animations = new Map();
  for (const source of sources) {
    const has = names => names.filter(name => AnimationClip.findByName(source.animations, name));
    for (const [name, clip] of retargetMotion(source, bones, has(MOTION_CLIPS), true)) animations.set(name, clip);
    for (const [name, clip] of retargetMotion(source, bones, has(ACTION_SOURCE_CLIPS), false)) animations.set(name, clip);
  }
  for (const name of [...MOTION_CLIPS, ...ACTION_SOURCE_CLIPS])
    if (!animations.has(name)) throw new Error(`Missing motion clip ${name}`);
  const gestures = readGestures(handClips, bones);
  const byName = new Map(bones.map(bone => [bone.name, bone]));
  const clipLayers = new Map(Object.entries(layers).map(([clip, layer]) => [clip, [
    ...Object.entries(layer.constant ?? {}).map(([name, q]) => ({ bone: byName.get(name.replace(":", "")), fixed: new Quaternion().fromArray(q) })),
    ...Object.entries(layer.tracks?.bones ?? {}).map(([name, list]) => ({
      bone: byName.get(name.replace(":", "")), rate: layer.tracks.rateHz, samples: list.map(q => new Quaternion().fromArray(q)),
    })),
  ].filter(entry => entry.bone)]));
  const correction = new Quaternion();
  const mixer = new AnimationMixer(model);
  let action;
  let logical;
  let queue = [];
  let overridden = [];

  function start(clipName) {
    const next = mixer.clipAction(animations.get(clipName)).reset();
    next.setLoop(ONE_SHOT.has(clipName) ? LoopOnce : LoopRepeat, Infinity);
    next.clampWhenFinished = ONE_SHOT.has(clipName);
    next.play();
    if (action && action !== next) next.crossFadeFrom(action, BLEND_SECONDS, false);
    action = next;
  }
  function plan(name, from) {
    if (name === "sit") return ["sit_down", "sit_idle"];
    if (name === "hold") return ["hold_item"];
    if (name === "box") return ["hold_box"];
    if (name === "bag") return ["hold_bag"];
    if (name === "take") return ["take_item"];
    return from === "sit" ? ["stand_up", name] : [name];
  }
  mixer.addEventListener("finished", event => {
    if (event.action === action && queue.length) start(queue.shift());
  });

  function restoreFingers() {
    // Last applied first, so a bone touched by a layer and a gesture ends on its mixer value.
    for (const { bone, baseline } of overridden.reverse()) bone.quaternion.copy(baseline);
    overridden = [];
  }

  return {
    select(name) {
      restoreFingers();
      queue = plan(name, logical);
      logical = name;
      start(queue.shift());
    },
    /** The clip that is actually playing, for example sit_idle while the "sit" choice is active. */
    get current() { return action?.getClip().name; },
    get time() { return action?.time; },
    update(delta, hands) {
      // Restore the last mixer sample first, even when playback is paused.
      // The mixer can skip writes whose interpolated value has not changed.
      restoreFingers();
      mixer.update(delta);
      for (const entry of clipLayers.get(action?.getClip().name) ?? []) {
        if (entry.fixed) correction.copy(entry.fixed);
        else {
          const position = ((action.time * entry.rate) % (entry.samples.length - 1) + entry.samples.length - 1) % (entry.samples.length - 1);
          const index = Math.floor(position);
          correction.copy(entry.samples[index]).slerp(entry.samples[index + 1], position - index);
        }
        entry.baseline ??= new Quaternion();
        entry.baseline.copy(entry.bone.quaternion);
        entry.bone.quaternion.multiply(correction);
        overridden.push(entry);
      }
      for (const side of HANDS) {
        const pose = gestures.get(`hand_${hands[side]}_${side}`);
        if (!pose) continue;
        for (const entry of pose) {
          entry.baseline.copy(entry.bone.quaternion);
          entry.bone.quaternion.copy(entry.pose);
          overridden.push(entry);
        }
      }
    },
    inspect() {
      return {
        clip: logical, playing: action?.getClip().name, time: action?.time, mixerTime: mixer.time,
        joints: bones.map((bone, index) => ({ name: bone.name, rest: rest[index], rotation: bone.quaternion.toArray() })),
      };
    },
    dispose() {
      restoreFingers();
      mixer.stopAllAction();
      mixer.uncacheRoot(model);
    },
  };
}

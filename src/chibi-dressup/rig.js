import { AnimationClip, AnimationMixer, PropertyBinding, Quaternion } from "three";
import { CLIPS, GESTURES, HANDS } from "./config.js";

const hips = "mixamorigHips";
const digits = {
  L: /^mixamorigLeftHand(?:Thumb|Index|Middle|Ring|Pinky)[1-4]$/,
  R: /^mixamorigRightHand(?:Thumb|Index|Middle|Ring|Pinky)[1-4]$/,
};
const targetTrack = (bone, property) => `${bone.uuid}.${property}`;

function retargetMotion(source, bones) {
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
    });
  }
  const quaternion = new Quaternion();
  return new Map(CLIPS.map(name => {
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
      } else if (nodeName === hips && propertyName === "position") {
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

export function createRig(model, skeleton, motion, handClips) {
  model.updateMatrixWorld(true);
  const bones = skeleton.bones;
  const rest = bones.map(bone => bone.quaternion.toArray());
  const animations = retargetMotion(motion, bones);
  const gestures = readGestures(handClips, bones);
  const mixer = new AnimationMixer(model);
  let action;
  let overridden = [];

  function restoreFingers() {
    for (const { bone, baseline } of overridden) bone.quaternion.copy(baseline);
    overridden = [];
  }

  return {
    select(name) {
      restoreFingers();
      mixer.stopAllAction();
      action = mixer.clipAction(animations.get(name)).reset().play();
    },
    update(delta, hands) {
      // Restore the last mixer sample first, even when playback is paused.
      // The mixer can skip writes whose interpolated value has not changed.
      restoreFingers();
      mixer.update(delta);
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
        clip: action?.getClip().name, time: action?.time, mixerTime: mixer.time,
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

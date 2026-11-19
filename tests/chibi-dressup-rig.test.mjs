import assert from "node:assert/strict";
import test from "node:test";
import { AnimationClip, Bone, Group, QuaternionKeyframeTrack, Quaternion, Skeleton } from "three";
import { GESTURES, HANDS, MOTION_CLIPS } from "../src/chibi-dressup/config.js";
import { createRig } from "../src/chibi-dressup/rig.js";

const NAMES = ["mixamorigHips", "mixamorigLeftHandThumb1", "mixamorigRightHandThumb1"];
const ACTIONS = ["sit_down", "sit_idle", "stand_up", "hold_item", "hold_box", "hold_bag", "take_item"];
const quarter = axis => new Quaternion().setFromAxisAngle(axis, Math.PI / 2).toArray();

function fixture(layers) {
  const make = () => {
    const root = new Group();
    const bones = NAMES.map(name => Object.assign(new Bone(), { name }));
    bones.forEach(bone => root.add(bone));
    root.updateMatrixWorld(true);
    return { root, bones };
  };
  const body = make();
  const source = make();
  source.root.animations = [];
  const identity = name => new QuaternionKeyframeTrack(`${name}.quaternion`, [0, 1], [0, 0, 0, 1, 0, 0, 0, 1]);
  const animations = [...MOTION_CLIPS, ...ACTIONS].map(name => new AnimationClip(name, 1, NAMES.map(identity)));
  const poses = HANDS.flatMap(side => GESTURES.map(gesture => {
    const bone = `mixamorig${side === "L" ? "Left" : "Right"}HandThumb1`;
    return new AnimationClip(`hand_${gesture}_${side}`, 0, [new QuaternionKeyframeTrack(`${bone}.quaternion`, [0], [0, 1, 0, 0])]);
  }));
  const skeleton = new Skeleton(body.bones);
  const rig = createRig(body.root, skeleton, [{ scene: source.root, animations }], poses, layers);
  return { rig, thumb: body.bones[2], other: body.bones[1] };
}

test("a clip layer multiplies a measured finger correction onto the animated joint, then gestures win", () => {
  const layer = { hold_box: { constant: { "mixamorig:RightHandThumb1": quarter({ x: 1, y: 0, z: 0 }) } } };
  const { rig, thumb, other } = fixture(layer);
  rig.select("box");
  rig.update(0.1, { L: null, R: null });
  assert.ok(thumb.quaternion.angleTo(new Quaternion().fromArray(layer.hold_box.constant["mixamorig:RightHandThumb1"])) < 1e-6);
  assert.ok(other.quaternion.angleTo(new Quaternion()) < 1e-6, "other joints stay on the animation");
  rig.update(0.1, { L: null, R: "fist" });
  assert.ok(thumb.quaternion.angleTo(new Quaternion(0, 1, 0, 0)) < 1e-6, "a chosen gesture overrides the layer");
  rig.update(0.1, { L: null, R: null });
  assert.ok(thumb.quaternion.angleTo(new Quaternion().fromArray(layer.hold_box.constant["mixamorig:RightHandThumb1"])) < 1e-6);
  rig.select("idle");
  rig.update(1, { L: null, R: null });
  assert.ok(thumb.quaternion.angleTo(new Quaternion()) < 1e-6, "other clips are untouched");
});

test("a looping track interpolates between its samples", () => {
  const half = new Quaternion().setFromAxisAngle({ x: 0, y: 0, z: 1 }, Math.PI / 2).toArray();
  const layer = { hold_box: { tracks: { rateHz: 2, bones: { "mixamorig:LeftHandThumb1": [[0, 0, 0, 1], half, [0, 0, 0, 1]] } } } };
  const { rig, other } = fixture(layer);
  rig.select("box");
  rig.update(0.25, { L: null, R: null });
  assert.ok(Math.abs(other.quaternion.angleTo(new Quaternion()) - Math.PI / 4) < 1e-3, "halfway to the first sample");
  rig.update(0.25, { L: null, R: null });
  assert.ok(Math.abs(other.quaternion.angleTo(new Quaternion()) - Math.PI / 2) < 1e-3);
});

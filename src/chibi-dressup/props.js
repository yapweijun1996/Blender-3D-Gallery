import { MathUtils } from "three";

// Prop sockets and events come from output/modular-chibi-parts/actions-astra and actions-hold2
// (attachment.json files): glTF joint-local transforms under mixamorig:RightHand.
const FPS = 24;
const SEAT_CLIPS = new Set(["sit_down", "sit_idle", "stand_up"]);
const HAND_SOCKETS = {
  hold_item: { prop: "cup", translation: [0.02593084, 0.02887651, 0.03611905], rotation: [0.27544212, 0.76551259, -0.46392176, 0.35056925] },
  hold_box: { prop: "box", translation: [0.18204346, 0.11279181, 0.10142164], rotation: [-0.86549461, -0.11057544, -0.44077593, 0.21073378] },
  hold_bag: { prop: "bag", translation: [0.02593105, 0.02887661, 0.0361193], rotation: [-0.83508277, 0.24741291, -0.34302348, 0.35179326] },
};
const JAR = {
  translation: [0.02593103, 0.02887667, 0.03611938], rotation: [-0.30049536, 0.01249045, -0.44810084, 0.84187424],
  returnStop: [-0.146, 0.523, 0.13], pickupStop: [-0.145, 0.523, 0.228],
  attachFrame: 29, returnFrames: [3, 16], cycleFrames: 48,
};
const smoothstep = x => x * x * (3 - 2 * x);

export function createProps({ root, hand, chair, cup, box, bag, shelf }) {
  const sockets = new Map();
  for (const [clip, { prop, translation, rotation }] of Object.entries(HAND_SOCKETS)) {
    const scene = { cup, box, bag }[prop];
    scene.visible = false;
    scene.position.fromArray(translation);
    scene.quaternion.fromArray(rotation);
    hand.add(scene);
    sockets.set(clip, scene);
  }
  chair.visible = false;
  root.add(chair);
  shelf.visible = false;
  root.add(shelf);
  const jar = shelf.getObjectByName("Jam_jar") ?? shelf.getObjectByName("Jam jar");
  if (!jar) throw new Error("Shelf prop has no jar");

  function placeJar(frame) {
    if (frame >= JAR.attachFrame) {
      if (jar.parent !== hand) hand.add(jar);
      jar.position.fromArray(JAR.translation);
      jar.quaternion.fromArray(JAR.rotation);
      return;
    }
    if (jar.parent !== shelf) shelf.add(jar);
    jar.quaternion.set(0, 0, 0, 1);
    const [start, end] = JAR.returnFrames;
    const amount = smoothstep(MathUtils.clamp((frame - start) / (end - start), 0, 1));
    jar.position.fromArray(JAR.returnStop).lerp({ x: JAR.pickupStop[0], y: JAR.pickupStop[1], z: JAR.pickupStop[2] }, amount);
  }

  return {
    /** Show the props that belong to the clip that is playing and move the shelf jar. */
    sync(clip, time) {
      chair.visible = SEAT_CLIPS.has(clip);
      for (const [name, scene] of sockets) scene.visible = clip === name;
      shelf.visible = clip === "take_item";
      if (shelf.visible) placeJar(Math.floor((time ?? 0) * FPS) % JAR.cycleFrames);
    },
  };
}

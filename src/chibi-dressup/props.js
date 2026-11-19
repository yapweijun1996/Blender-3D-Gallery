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

/**
 * `fitted` may override the neutral-body grips per body: { hold_item|hold_box|hold_bag|jar: { translation, rotation }, chair|shelf: { translation, scale }, jar may add returnStop and pickupStop }.
 * Hand bones differ between bodies, so each body brings its own measured sockets.
 */
export function createProps({ root, hand, chair, cup, box, bag, shelf, fitted = {} }) {
  const sockets = new Map();
  const grip = { ...JAR, ...fitted.jar }; // may also carry returnStop and pickupStop
  for (const [clip, base] of Object.entries(HAND_SOCKETS)) {
    const { prop, translation, rotation } = { ...base, ...fitted[clip] };
    const scene = { cup, box, bag }[prop];
    scene.visible = false;
    scene.position.fromArray(translation);
    scene.quaternion.fromArray(rotation);
    hand.add(scene);
    sockets.set(clip, scene);
  }
  chair.visible = false;
  if (fitted.chair) {
    chair.position.fromArray(fitted.chair.translation);
    chair.scale.fromArray(fitted.chair.scale);
  }
  root.add(chair);
  shelf.visible = false;
  if (fitted.shelf) {
    shelf.position.fromArray(fitted.shelf.translation);
    shelf.scale.fromArray(fitted.shelf.scale);
  }
  root.add(shelf);
  const jar = shelf.getObjectByName("Jam_jar") ?? shelf.getObjectByName("Jam jar");
  if (!jar) throw new Error("Shelf prop has no jar");

  function placeJar(frame) {
    if (frame >= JAR.attachFrame) {
      if (jar.parent !== hand) hand.add(jar);
      jar.position.fromArray(grip.translation);
      jar.quaternion.fromArray(grip.rotation);
      return;
    }
    if (jar.parent !== shelf) shelf.add(jar);
    jar.quaternion.set(0, 0, 0, 1);
    const [start, end] = JAR.returnFrames;
    const amount = smoothstep(MathUtils.clamp((frame - start) / (end - start), 0, 1));
    jar.position.fromArray(grip.returnStop).lerp({ x: grip.pickupStop[0], y: grip.pickupStop[1], z: grip.pickupStop[2] }, amount);
  }

  return {
    /** Remove the props from this body so another body can carry them; the shared models stay loaded. */
    detach() {
      for (const scene of [...sockets.values(), chair, shelf, jar]) scene.parent?.remove(scene);
      shelf.add(jar); // The jar goes back to its shelf so the next body finds it there.
      for (const scene of [...sockets.values(), chair, shelf]) scene.visible = false;
    },
    /** Show the props that belong to the clip that is playing and move the shelf jar. */
    sync(clip, time) {
      chair.visible = SEAT_CLIPS.has(clip);
      for (const [name, scene] of sockets) scene.visible = clip === name;
      shelf.visible = clip === "take_item";
      if (shelf.visible) placeJar(Math.floor((time ?? 0) * FPS) % JAR.cycleFrames);
      else if (jar.parent !== shelf) shelf.add(jar); // A jar taken in the hand does not follow other clips.
    },
  };
}

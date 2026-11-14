import { AnimationMixer, LoopOnce } from "three";

export const POSES = Object.freeze({ closed: null, open: "OpenClose", exploded: "Exploded" });
export const REQUIRED_NODES = ["ASSET_DemoFoodTin", "BODY_HollowShell", "MOVABLE_Lid", "MOVABLE_PullRing"];
/** Authored clips are the only authority for movement. No synthetic lid offsets. */
export function createPoseController(gltf) {
  for (const name of REQUIRED_NODES) if (!gltf.scene.getObjectByName(name)) throw new Error("Missing packaging node: " + name);
  const clips = new Map(gltf.animations.map(c => [c.name, c]));
  for (const name of ["OpenClose", "Exploded"]) {
    const clip = clips.get(name);
    if (!clip || Math.abs(clip.duration - 3) > 1e-4 || !clip.tracks.length)
      throw new Error("Invalid packaging animation: " + name);
    if (clip.tracks.some(t => Math.abs(t.times[0]) > 1e-6))
      throw new Error("Packaging animations must start at zero");
  }
  const rest = [];
  gltf.scene.traverse(node => rest.push({ node, position: node.position.clone(), quaternion: node.quaternion.clone(), scale: node.scale.clone() }));
  const mixer = new AnimationMixer(gltf.scene);
  let disposed = false;
  function apply(mode, amount = 1) {
    if (disposed) throw new Error("Packaging controller disposed");
    if (!Object.hasOwn(POSES, mode) || !Number.isFinite(amount) || amount < 0 || amount > 1) throw new Error("Invalid packaging pose");
    mixer.stopAllAction();
    for (const r of rest) { r.node.position.copy(r.position); r.node.quaternion.copy(r.quaternion); r.node.scale.copy(r.scale); }
    if (POSES[mode]) {
      const action = mixer.clipAction(clips.get(POSES[mode]));
      action.reset().setLoop(LoopOnce, 1); action.clampWhenFinished = true;
      action.play(); action.paused = true; action.time = amount * 1.5;
      mixer.update(0);
    }
    gltf.scene.updateMatrixWorld(true);
  }
  return { apply, dispose() { if (disposed) return; apply("closed"); disposed = true; mixer.stopAllAction(); mixer.uncacheRoot(gltf.scene); } };
}

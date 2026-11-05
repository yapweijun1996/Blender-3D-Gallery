import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { Vector3 } from "three";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { TABLE, makeRack } from "../src/game/table.js";
import { createShot, stepPhysics } from "../src/game/physics.js";

for (const name of ["ball_01", "ball_09"]) {
  test(`${name} real GLB rolls its contact point against the direction of travel`, async () => {
    const bytes = await readFile(new URL(`../models/eight-ball-billiards/exports/${name}.glb`, import.meta.url));
    const model = await new GLTFLoader().parseAsync(bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength), "");
    let target = null;
    model.scene.traverse((mesh) => {
      if (!mesh.isMesh) return;
      const positions = mesh.geometry.attributes.position;
      for (let i = 0; i < positions.count; i++) {
        const point = new Vector3().fromBufferAttribute(positions, i);
        const error = point.distanceTo(new Vector3(0, -TABLE.radius, 0));
        if (!target || error < target.error) target = { mesh, point, error };
      }
    });
    assert.ok(target && target.error < 1e-6, "asset has a bottom contact point at its origin");
    model.scene.updateMatrixWorld(true);
    const start = target.mesh.localToWorld(target.point.clone());
    const balls = makeRack();
    for (const ball of balls) ball.pocketed = ball.id !== 0;
    Object.assign(balls[0], { x: 0, z: 0, vx: 0, vz: 0, q: [0, 0, 0, 1], pocketed: false });
    const shot = createShot(balls, { x: 1, z: 0 }, 0.1);
    for (let i = 0; i < 12; i++) stepPhysics(balls, shot);
    const ball = balls[0];
    model.scene.position.set(ball.x, 0, ball.z);
    model.scene.quaternion.fromArray(ball.q);
    model.scene.updateMatrixWorld(true);
    const end = target.mesh.localToWorld(target.point.clone());
    const expected = ball.x - TABLE.radius * Math.sin(ball.x / TABLE.radius);
    assert.ok(Math.abs(end.x - start.x - expected) < 1e-7, `contact moved ${end.x - start.x}; expected ${expected}`);
    assert.ok(end.x - start.x < ball.x, "contact turns backwards relative to the moving centre");
  });
}

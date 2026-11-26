import { MathUtils, Matrix4, Vector3 } from 'three';

export const entranceDuration = 3.12;
export const entranceBudgetMs = 6000;
export const loopStart = .74;
export const loopEnd = 2.04;
export const maxFrameDelta = 1 / 30;
const initialDistance = 2.95;
const horizontalAxis = new Vector3(1, 0, 0);

export function frameDelta(now, last) {
  return last === null ? 0 : MathUtils.clamp((now - last) / 1000, 0, maxFrameDelta);
}

export function createEntranceFlight(envelope, camera, width) {
  const pitch = camera.rotation.x;
  const { y: aim, z: distance } = camera.position.clone().applyAxisAngle(horizontalAxis, -pitch);
  const xScale = camera.projectionMatrix.elements[0];
  const flight = { pitch, aim, distance, radius: MathUtils.clamp(.38 * distance / xScale, .5, .96), startX: 0 };
  poseEntrance(envelope, 0, flight);
  envelope.updateMatrixWorld(true);
  const point = new Vector3(), toView = new Matrix4();
  const left = -1 - 4 / width; // Two CSS pixels outside the viewport.
  let start = Infinity;
  envelope.traverseVisible(object => {
    if (!object.isMesh) return;
    toView.multiplyMatrices(camera.matrixWorldInverse, object.matrixWorld);
    const positions = object.geometry.attributes.position;
    for (let i = 0; i < positions.count; i++) {
      point.fromBufferAttribute(positions, i).applyMatrix4(toView);
      const depth = -point.z;
      point.applyMatrix4(camera.projectionMatrix);
      // The camera pitches about X, so moving sideways leaves depth fixed.
      start = Math.min(start, (left - point.x) * depth / xScale);
    }
  });
  flight.startX = start / initialDistance;
  return flight;
}

export function poseEntrance(envelope, time, flight) {
  const approach = MathUtils.smoothstep(time, 0, loopStart);
  const angle = 2 * Math.PI * MathUtils.smoothstep(time, loopStart, loopEnd);
  const landing = MathUtils.smootherstep(time, loopEnd, 2.89);
  const settle = MathUtils.smoothstep(time, 2.89, entranceDuration);
  const turn = MathUtils.smootherstep(time, 2.17, 2.86);
  const bank = MathUtils.smoothstep(time, .5, loopStart) * (1 - MathUtils.smoothstep(time, loopEnd, 2.19));
  const depth = 1 + 1.3 * (1 - MathUtils.smoothstep(time, 0, 1.22)) +
    .65 * (1 - MathUtils.smoothstep(time, 2.08, 2.92));
  // Shape the loop in the camera plane, then place it at its true depth.
  const x = MathUtils.lerp(flight.startX, -flight.radius, approach) +
    flight.radius * (1 - Math.cos(angle)) + (flight.radius + .055) * landing - .055 * settle;
  const y = MathUtils.lerp(.26, .67, approach) + .83 * Math.sin(angle) - .67 * landing;
  envelope.position.set(
    x * depth, flight.aim + (y - flight.aim) * depth, flight.distance * (1 - depth),
  ).applyAxisAngle(horizontalAxis, flight.pitch);
  envelope.rotation.set(
    -.14 * bank * Math.sin(angle),
    (Math.PI - .16 + .23 * bank * Math.sin(angle)) * (1 - turn),
    .13 * (1 - approach) - .28 * bank * Math.cos(angle) + .06 * Math.sin(Math.PI * landing),
  );
}

export function poseRecedingEnvelope(envelope, time) {
  const recession = MathUtils.smoothstep(time, 0, .8);
  envelope.position.set(0, -.58 * recession, -2.05 * recession);
}

export function poseIdle(envelope, time, weight = 1) {
  envelope.position.set(0, weight * .037 * Math.sin(time * 1.25), 0);
  envelope.rotation.set(
    weight * .021 * Math.sin(time * 1.06),
    weight * .030 * Math.sin(time * .76),
    weight * .017 * Math.sin(time * .89),
  );
}

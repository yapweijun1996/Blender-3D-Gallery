// Contact targets are the lowest native sneaker vertices in machine-local metres.
// The caller samples the original idle pose before measuring the leg geometry.
import { Matrix4, Quaternion, Vector3 } from 'three';

const point = (x = 0, y = 0, z = 0) => new Vector3(x, y, z);
const rotation = () => new Quaternion();
function nativeFrame(reference) {
  const inverse = new Matrix4();
  const orientation = rotation();
  function refresh() {
    reference.updateWorldMatrix(true, false);
    inverse.copy(reference.matrixWorld).invert();
    reference.getWorldQuaternion(orientation);
  }
  refresh();
  return {
    refresh,
    orientation,
    position: (node) => node.getWorldPosition(point()).applyMatrix4(inverse),
    fromWorld: (p) => p.applyMatrix4(inverse),
  };
}

function makeLeg(avatar, name, frame) {
  const hip = avatar.getObjectByName(name + 'Hip');
  const knee = avatar.getObjectByName(name + 'Knee');
  const ankle = avatar.getObjectByName(name + 'Foot');
  const pole = point(0, Infinity, 0);
  ankle.traverse((node) => {
    if (!node.isMesh) return;
    for (let i = 0; i < node.geometry.attributes.position.count; i++) {
      const candidate = frame.fromWorld(node.getVertexPosition(i, point()).applyMatrix4(node.matrixWorld));
      if (candidate.y < pole.y) pole.copy(candidate);
    }
  });
  const hipPosition = frame.position(hip),
    kneePosition = frame.position(knee),
    anklePosition = frame.position(ankle);
  const thighLength = hipPosition.distanceTo(kneePosition),
    shinLength = kneePosition.distanceTo(anklePosition);
  const hipFromRoot = hipPosition.clone().sub(frame.position(avatar));
  const poleFromRoot = pole.clone().sub(frame.position(avatar));
  const ankleFromPole = anklePosition.clone().sub(pole);
  const neutralSlack =
    Math.sqrt((thighLength + shinLength) ** 2 - (hipPosition.z - anklePosition.z) ** 2) -
    (hipPosition.y - anklePosition.y);
  return {
    hip,
    knee,
    ankle,
    hipFromRoot,
    poleFromRoot,
    ankleFromPole,
    neutralSlack,
    thighLength,
    shinLength,
    neutralRotations: [hip, knee, ankle].map((joint) => joint.quaternion.clone()),
    neutralAnkleRotation: frame.orientation.clone().invert().multiply(ankle.getWorldQuaternion(rotation())),
  };
}

function aimAt(joint, child, direction, frame) {
  const localDirection = direction
    .clone()
    .applyQuaternion(frame.orientation)
    .applyQuaternion(joint.parent.getWorldQuaternion(rotation()).invert())
    .normalize();
  joint.quaternion.setFromUnitVectors(child.position.clone().normalize(), localDirection);
  joint.updateWorldMatrix(false, true);
}

function solveLeg(leg, target, bendSide, frame) {
  const { hip, knee, ankle, thighLength, shinLength } = leg;
  const hipPosition = frame.position(hip);
  const anklePosition = target.clone().add(leg.ankleFromPole);
  const direction = anklePosition.clone().sub(hipPosition);
  const distance = direction.length();
  if (distance > thighLength + shinLength + 1e-6 || distance < Math.abs(thighLength - shinLength) - 1e-6) {
    throw new Error('Contact target exceeds native leg reach');
  }
  direction.divideScalar(distance);
  const along = (thighLength * thighLength - shinLength * shinLength + distance * distance) / (2 * distance);
  const altitude = Math.sqrt(Math.max(0, thighLength * thighLength - along * along));
  // Choose the sagittal solution that flexes toward the direction of walking.
  // The tiny opposite branch at rest matches the native ankle offset.
  const normal = point(0, -direction.z, direction.y);
  const kneePosition = hipPosition
    .clone()
    .addScaledVector(direction, along)
    .addScaledVector(normal, bendSide * altitude);
  aimAt(hip, knee, kneePosition.clone().sub(hipPosition), frame);
  aimAt(knee, ankle, anklePosition.clone().sub(frame.position(knee)), frame);
  ankle.quaternion
    .copy(knee.getWorldQuaternion(rotation()).invert())
    .multiply(frame.orientation)
    .multiply(leg.neutralAnkleRotation);
  ankle.updateWorldMatrix(false, true);
}

export function createContactRig(avatar, reference) {
  const frame = nativeFrame(reference);
  avatar.updateWorldMatrix(true, true);
  const feet = [makeLeg(avatar, 'Left', frame), makeLeg(avatar, 'Right', frame)];
  const forwardBend = -Math.sign(point(0, 0, 1).applyQuaternion(avatar.quaternion).z);
  function pose({ left, right, stretch = 1 }) {
    frame.refresh();
    const targets = [left, right];
    const rootZ = targets.reduce((sum, pole, i) => sum + pole.z - feet[i].poleFromRoot.z, 0) / 2;
    const stride = Math.abs(left.z - right.z);
    const crouch = 0.012 * Math.min(1, stride / 0.5) ** 2;
    let rootY = Infinity;
    for (let i = 0; i < 2; i++) {
      const foot = feet[i],
        target = targets[i];
      if (Math.abs(foot.poleFromRoot.x - target.x) > 1e-5)
        throw new Error('Sagittal solve needs fixed native shoe lanes');
      const dz = target.z + foot.ankleFromPole.z - (rootZ + foot.hipFromRoot.z);
      const reachY = Math.sqrt((foot.thighLength + foot.shinLength) ** 2 - dz * dz);
      if (!Number.isFinite(reachY)) throw new Error('Stance is wider than the native leg reach');
      rootY = Math.min(
        rootY,
        target.y +
          foot.ankleFromPole.y +
          reachY -
          foot.hipFromRoot.y -
          foot.neutralSlack * stretch ** 2 -
          crouch,
      );
    }
    avatar.position.set(0, rootY, rootZ);
    avatar.updateWorldMatrix(true, true);
    for (let i = 0; i < 2; i++)
      solveLeg(feet[i], targets[i], stretch < 0 ? -forwardBend : forwardBend, frame);
  }
  function restoreLegs() {
    for (const leg of feet) {
      [leg.hip, leg.knee, leg.ankle].forEach((joint, i) => joint.quaternion.copy(leg.neutralRotations[i]));
    }
  }
  return { feet, pose, restoreLegs };
}

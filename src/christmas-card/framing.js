import { Euler, MathUtils, Quaternion, Vector3 } from 'three';

const pitch = .13;
const fov = 23;
const closePitch = .225;
const closeRoll = .044;
const axis = new Vector3(1, 0, 0);
const hinge = new Vector3(0, 1.044, -.073);
const frameBounds = [];

function addBox(bounds, x, bottom, top, back, front) {
  for (const y of [bottom, top]) {
    for (const z of [back, front]) bounds.push(new Vector3(x, y, z));
  }
}

// Symmetric support points for the body (including idle sway), seal and letter.
addBox(frameBounds, 1.625, -1.11, 1.11, -.15, .125);
addBox(frameBounds, .42, -.56, .29, .08, .27);
const closeBounds = [];
addBox(closeBounds, 1.605, -1.055, 1.055, -.09, .075);
addBox(closeBounds, .42, -.56, .29, .08, .27);
addBox(frameBounds, 1.48, -.96, 2.20, -.05, .024);
// Sweep the tapered flap about its hinge. A rectangular box around the sweep
// would reserve space for corners that never exist and shrink the mobile card.
const flap = [
  [1.61, .015, .015], [1.47, -.095, .167],
  [.135, -1.255, .167], [.02, -1.305, .155],
];
for (let degrees = 0; degrees <= 174; degrees += 3) {
  for (const [x, y, z] of flap) {
    const point = new Vector3(x, y, z).applyAxisAngle(axis, -MathUtils.degToRad(degrees)).add(hinge);
    frameBounds.push(point);
    // The close shot peaks during the swing, before the flap and letter rise fully.
    if (degrees <= 120) closeBounds.push(point);
  }
}
// Maximum reach of the existing burst, including the particle radii.
const burstBounds = [...frameBounds];
addBox(burstBounds, 1.48, 1.15, 3.10, -.05, .024);
addBox(burstBounds, 2.25, -.12, 3.65, -.5, .82);
const closeRotation = new Quaternion().setFromEuler(new Euler(-closePitch, 0, closeRoll));
const inverseClose = closeRotation.clone().invert();
const angledBounds = closeBounds.flatMap(({ x, y, z }) => [
  new Vector3(x, y, z).applyQuaternion(inverseClose),
  new Vector3(-x, y, z).applyQuaternion(inverseClose),
]);
const idleBounds = frameBounds.map(point => point.clone().applyAxisAngle(axis, pitch));
const wideBounds = burstBounds.map(point => point.clone().applyAxisAngle(axis, pitch));
const liftedPaper = [];
addBox(liftedPaper, 1.48, 1.14, 3.06, -.05, .024);
const widePaperBounds = liftedPaper.map(point => point.applyAxisAngle(axis, pitch));

function fitBounds(bounds, xSlope, topSlope, bottomSlope, aim, minimumDistance = 0, paperSlope = topSlope) {
  let distance = minimumDistance, upperEdge = -Infinity, lowerEdge = Infinity;
  for (const { x, y, z } of bounds) {
    distance = Math.max(distance, z + Math.abs(x) / xSlope);
    upperEdge = Math.max(upperEdge, y + z * topSlope);
    lowerEdge = Math.min(lowerEdge, y - z * bottomSlope);
  }
  // Each point constrains the vertical aim at a given distance. Move the
  // camera back just enough for all those intervals to overlap.
  distance = Math.max(distance, (upperEdge - lowerEdge) / (topSlope + bottomSlope));
  let paperEdge = -Infinity;
  if (paperSlope < topSlope) {
    for (const {y, z} of widePaperBounds) paperEdge = Math.max(paperEdge, y + z * paperSlope);
    distance = Math.max(distance, (paperEdge - lowerEdge) / (paperSlope + bottomSlope));
  }
  const topAim = Math.max(upperEdge - distance * topSlope, paperEdge - distance * paperSlope);
  const center = MathUtils.clamp(aim, topAim, lowerEdge + distance * bottomSlope);
  return new Vector3(0, center, distance);
}

export function frameEnvelope(camera, viewport, stage) {
  const tangent = Math.tan(MathUtils.degToRad(fov / 2));
  const entrance = fitBounds(idleBounds, tangent * stage.width / stage.height * .985, tangent * .99, tangent * .99, .36);
  const x = stage.left + stage.width / 2 - viewport.left;
  const y = stage.top + stage.height / 2 - viewport.top;
  const slope = 2 * tangent / stage.height;
  const halfWidth = Math.min(x, viewport.width - x);
  const closeDistance = entrance.z * .67;
  const closeWidth = 2 * (halfWidth - 5) / stage.height;
  // Widen the lens on narrow screens so the camera can get physically closer
  // without cropping the mouth. Desktop has room for the tighter lens.
  const closeTangent = angledBounds.reduce((value, point) =>
    Math.max(value, Math.abs(point.x) / ((closeDistance - point.z) * closeWidth)), tangent);
  const closeSlope = 2 * closeTangent / stage.height;
  const close = fitBounds(angledBounds, closeSlope * (halfWidth - 5), closeSlope * (y - 9),
    closeSlope * (viewport.height - y - 9), .73, closeDistance);
  // Keep room for the paper's upward arc as it leaves the wide shot.
  const wide = fitBounds(wideBounds, slope * (halfWidth - 10),
    slope * (y - 10), slope * (viewport.height - y - 10), .93, entrance.z * 1.04,
    slope * (stage.height / 2 - 30));
  camera.fov = fov;
  camera.far = Math.max(50, entrance.z * 3.2);
  // Extend the view outside the composition area so the flight can cross
  // the full viewport while the settled envelope keeps its size and position.
  camera.setViewOffset(stage.width, stage.height, viewport.left - stage.left,
    viewport.top - stage.top, viewport.width, viewport.height);
  entrance.applyAxisAngle(axis, -pitch);
  wide.applyAxisAngle(axis, -pitch);
  close.applyQuaternion(closeRotation);
  const restPullback = .24 * (1 - MathUtils.smoothstep(viewport.width, 415, 620));
  const views = {
    restPullback,
    entrance: { position: entrance, pitch, roll: 0, fov },
    idle: { position: entrance.clone().multiplyScalar(1 + restPullback), pitch, roll: 0, fov },
    close: { position: close, pitch: closePitch, roll: closeRoll, fov: MathUtils.radToDeg(2 * Math.atan(closeTangent)) },
    wide: { position: wide, pitch, roll: 0, fov },
  };
  setCameraPose(camera, views.idle);
  return views;
}

export function poseLandingCamera(camera, views, center, time) {
  if (!views.restPullback) return;
  const pullback = views.restPullback * MathUtils.smootherstep(time, 2.68, 3.12);
  // Pull back along the sight line to keep the approved projected flight path.
  camera.position.copy(views.entrance.position).multiplyScalar(1 + pullback).addScaledVector(center, -pullback);
  camera.updateMatrixWorld();
}

function aimCamera(camera, angle, roll, lens) {
  camera.rotation.set(-angle, 0, roll);
  if (camera.fov !== lens) {
    camera.fov = lens;
    camera.updateProjectionMatrix();
  }
  camera.updateMatrixWorld();
}

export function setCameraPose(camera, pose) {
  camera.position.copy(pose.position);
  aimCamera(camera, pose.pitch, pose.roll, pose.fov);
}

export function poseOpeningCamera(camera, views, time, burstTime) {
  const peak = .6 * burstTime;
  const pushing = time < peak;
  const from = pushing ? views.idle : views.close;
  const to = pushing ? views.close : views.wide;
  const ease = pushing ? MathUtils.smoothstep(time, 0, peak) : MathUtils.smoothstep(time, peak, burstTime + .22);
  const interpolate = MathUtils.lerp;
  camera.position.lerpVectors(from.position, to.position, ease);
  const lens = from.fov === to.fov ? from.fov : interpolate(from.fov, to.fov, ease);
  aimCamera(camera, interpolate(from.pitch, to.pitch, ease), interpolate(from.roll, to.roll, ease),
    lens);
  return pushing ? ease : 1 - ease;
}

import RAPIER from "@dimforge/rapier3d-compat";
import { CRASH_TUNING, createCrashState, upDot, uprightRotation } from "./crash.js";

const DOWN = { x: 0, y: -1, z: 0 };
// Rapier computes the rolling direction as the contact normal crossed with the axle.
const AXLE = { x: -1, y: 0, z: 0 };
const WHEEL_FILTER = RAPIER.QueryFilterFlags.EXCLUDE_DYNAMIC |
  RAPIER.QueryFilterFlags.EXCLUDE_KINEMATIC | RAPIER.QueryFilterFlags.EXCLUDE_SENSORS;

export const VEHICLE_TUNING = Object.freeze({
  restLength: 0.30,
  stiffness: 24,
  damping: 2.4,
  travel: 0.25,
  suspensionForceWeight: 2,
  frictionSlip: 1.5,
  sideFriction: 1,
  handbrakeSlip: 0.6,
  handbrakeSideFriction: 0.35,
  handbrakeMultiplier: 1.5,
  lowSpeedSteer: 0.55,
  highSpeedSteer: 0.12,
  highSpeed: 30,
  governorBand: 3,
  antiRollSpring: 8,
  antiRollDamping: 0.7,
  maximumLean: 0.40,
  fullLeanSpeed: 12,
  bikeRollSpring: 36,
  bikeRollDamping: 11,
  chassisFriction: 0.55,
  angularDamping: 0.35,
  gears: Object.freeze([
    Object.freeze({ below: 8, multiplier: 1.00 }),
    Object.freeze({ below: 15, multiplier: 0.85 }),
    Object.freeze({ below: 23, multiplier: 0.72 }),
    Object.freeze({ below: 32, multiplier: 0.61 }),
    Object.freeze({ below: Infinity, multiplier: 0.52 }),
  ]),
});

function profile(mass, topSpeed, engineForce, brakeForce, size, wheelRadius, track, mountY, front, rear) {
  const [x, y, z] = size;
  const wheelPositions = track === 0
    ? [{ x: 0, y: mountY, z: front }, { x: 0, y: mountY, z: rear }]
    : [
        { x: track, y: mountY, z: front },
        { x: -track, y: mountY, z: front },
        { x: track, y: mountY, z: rear },
        { x: -track, y: mountY, z: rear },
      ];
  return Object.freeze({
    mass, topSpeed, engineForce, brakeForce,
    chassisHalfExtents: Object.freeze({ x, y, z }),
    wheelRadius,
    wheelPositions: Object.freeze(wheelPositions.map((point) => Object.freeze(point))),
  });
}

// Forces are total axle/vehicle forces in N. Speeds are in m/s, geometry in m.
export const VEHICLE_TYPES = Object.freeze({
  hatchback: profile(1100, 42, 7800, 8500, [0.84, 0.32, 1.82], 0.34, 0.76, -0.12, 1.23, -1.23),
  sedan: profile(1300, 50, 9300, 9500, [0.88, 0.34, 2.10], 0.35, 0.80, -0.13, 1.40, -1.40),
  van: profile(2200, 35, 12000, 14000, [1.00, 0.65, 2.43], 0.39, 0.89, -0.40, 1.57, -1.57),
  bus: profile(12000, 25, 45000, 54000, [1.24, 1.12, 5.60], 0.53, 1.04, -0.76, 3.50, -3.50),
  lorry: profile(9000, 29, 38000, 45000, [1.20, 0.89, 4.25], 0.51, 1.02, -0.57, 2.60, -2.60),
  motorbike: profile(180, 47, 1350, 1300, [0.20, 0.30, 0.88], 0.31, 0, -0.12, 0.68, -0.68),
});

const neutral = Object.freeze({ throttle: 0, brake: 0, steer: 0, handbrake: 0, reverse: 0 });
const REVERSE_TOP_SPEED = 6; // m/s
const clamp = (value, min, max) => Math.max(min, Math.min(max, value));
const input = (value, min = 0) => Number.isFinite(value) ? clamp(value, min, 1) : 0;

function forward({ x, y, z, w }) {
  return { x: 2 * (x * z + w * y), y: 2 * (y * z - w * x), z: 1 - 2 * (x * x + y * y) };
}

function dot(a, b) {
  return a.x * b.x + a.y * b.y + a.z * b.z;
}

function bikeRoll(rotation) {
  const { x, y, z, w } = rotation;
  return Math.atan2(2 * (x * y + w * z), upDot(rotation));
}

/**
 * Creates the chassis and wheel controller in a Rapier world. Use the physics world's
 * addVehicle() to automatically step the controller, track crashes and own its lifetime.
 * X is east, Y is up, Z is south and the nose points along local +Z. Positive steer
 * and positive heading (rotation.y) turn left: from +Z toward +X.
 * Wheel positions are chassis-local mounts in front-left, front-right, rear-left,
 * rear-right order. For the motorbike the order is front, rear.
 */
export function createVehicle(world, options = {}) {
  const { type = "hatchback", heading = 0 } = options;
  if (!Object.hasOwn(VEHICLE_TYPES, type)) throw new RangeError(`Unknown vehicle type: ${type}`);

  const { mass, topSpeed, engineForce, brakeForce, chassisHalfExtents, wheelRadius, wheelPositions } = {
    ...VEHICLE_TYPES[type], ...options,
  };
  const bike = type === "motorbike";
  const axleSize = bike ? 1 : 2;
  const wheelCount = axleSize * 2;
  if (!Array.isArray(wheelPositions) || wheelPositions.length !== wheelCount) {
    throw new RangeError(`Expected ${wheelCount} wheel positions`);
  }
  const mounts = Array.from(wheelPositions, ({ x, y, z }) => ({ x, y, z }));
  const { x: halfWidth, y: halfHeight, z: halfLength } = chassisHalfExtents;
  if (![mass, topSpeed, brakeForce, wheelRadius, halfWidth, halfHeight, halfLength]
    .every((value) => Number.isFinite(value) && value > 0)
    || !Number.isFinite(engineForce) || engineForce < 0) {
    throw new RangeError("Expected positive vehicle dimensions, mass, top speed and braking force, and nonnegative engine force");
  }
  if (!mounts.every(({ x, y, z }) => [x, y, z].every(Number.isFinite))) {
    throw new RangeError("Expected finite wheel mount coordinates");
  }

  const tuning = VEHICLE_TUNING;
  const restHeight = wheelRadius + tuning.restLength - Math.min(...mounts.map(({ y }) => y));
  const spawnHeight = Math.max(restHeight, halfHeight + 0.05);
  const position = options.position ?? { x: 0, y: spawnHeight, z: 0 };
  if (![heading, position.x, position.y, position.z].every(Number.isFinite)) {
    throw new RangeError("Expected a finite position and heading");
  }
  const body = world.createRigidBody(RAPIER.RigidBodyDesc.dynamic()
    .setTranslation(position.x, position.y, position.z)
    .setRotation(uprightRotation(heading))
    .setAngularDamping(tuning.angularDamping)
    // Raycast support does not create solver contacts that can wake a sleeping body.
    .setCanSleep(false)
    .setCcdEnabled(true));
  const collider = world.createCollider(RAPIER.ColliderDesc
    .cuboid(halfWidth, halfHeight, halfLength)
    .setMass(mass)
    .setFriction(tuning.chassisFriction)
    .setActiveEvents(RAPIER.ActiveEvents.CONTACT_FORCE_EVENTS)
    .setContactForceEventThreshold(0), body);
  const crash = createCrashState(body, mass);
  const maxSuspensionForce = mass * Math.hypot(world.gravity.x, world.gravity.y, world.gravity.z)
    * tuning.suspensionForceWeight;
  let controls = neutral;
  let gear = 1;
  let controller = makeController();

  function makeController() {
    const result = world.createVehicleController(body);
    result.indexUpAxis = 1;
    result.setIndexForwardAxis = 2;
    for (const [index, mount] of mounts.entries()) {
      result.addWheel(mount, DOWN, AXLE, tuning.restLength, wheelRadius);
      result.setWheelSuspensionStiffness(index, tuning.stiffness);
      result.setWheelSuspensionCompression(index, tuning.damping);
      result.setWheelSuspensionRelaxation(index, tuning.damping);
      result.setWheelMaxSuspensionTravel(index, tuning.travel);
      result.setWheelMaxSuspensionForce(index, maxSuspensionForce);
      result.setWheelFrictionSlip(index, tuning.frictionSlip);
      result.setWheelSideFrictionStiffness(index, tuning.sideFriction);
    }
    return result;
  }

  function stabilizeRoll(dt, rotation, direction, speed, steering, rollBeforeWheels) {
    const rollSpeed = dot(body.angvel(), direction);
    let impulse = 0;
    if (bike) {
      if (!controller.wheelIsInContact(0) && !controller.wheelIsInContact(1)) return;
      const leanTarget = -tuning.maximumLean * (steering / tuning.lowSpeedSteer)
        * Math.min(1, speed / tuning.fullLeanSpeed);
      // The raycast tires act below the center of mass. Counter their roll impulse
      // so a two-wheel chassis can balance and follow its intended cornering lean.
      const rollAcceleration = tuning.bikeRollSpring * (leanTarget - bikeRoll(rotation))
        - tuning.bikeRollDamping * rollBeforeWheels;
      impulse = body.principalInertia().z * (rollAcceleration * dt - (rollSpeed - rollBeforeWheels));
    } else {
      for (const left of [0, 2]) {
        const right = left + 1;
        if (!controller.wheelIsInContact(left) || !controller.wheelIsInContact(right)) continue;
        const travelDifference = controller.wheelSuspensionLength(right) - controller.wheelSuspensionLength(left);
        impulse += mass * dt * (tuning.antiRollSpring * travelDifference - tuning.antiRollDamping * rollSpeed);
      }
    }
    if (impulse !== 0) {
      body.applyTorqueImpulse({ x: direction.x * impulse, y: direction.y * impulse, z: direction.z * impulse }, true);
    }
  }

  return {
    type, body, collider, crash,

    /** Each call supplies a complete control sample. Steer is [-1, 1], other inputs [0, 1]. */
    setControls({ throttle, brake, steer, handbrake, reverse } = {}) {
      controls = {
        throttle: input(throttle), brake: input(brake), steer: input(steer, -1),
        handbrake: handbrake === true ? 1 : input(handbrake), reverse: input(reverse),
      };
      if (controls.throttle || controls.brake || controls.steer || controls.handbrake || controls.reverse) body.wakeUp();
    },

    update(dt) {
      const rotation = body.rotation();
      const direction = forward(rotation);
      const velocity = body.linvel();
      const speed = Math.hypot(velocity.x, velocity.z);
      const forwardSpeed = dot(direction, velocity);
      const { throttle, brake, steer, handbrake, reverse } = controls;
      const steering = steer * (tuning.lowSpeedSteer + (tuning.highSpeedSteer - tuning.lowSpeedSteer)
        * Math.min(speed / tuning.highSpeed, 1));
      gear = tuning.gears.findIndex(({ below }) => speed < below) + 1;
      const upright = upDot(rotation) >= CRASH_TUNING.flippedUpDot && !crash.flipped;
      const speedScale = clamp((topSpeed - forwardSpeed) / tuning.governorBand, 0, 1);
      // Grounded wheels govern forward speed through tire forces, leaving crash/airborne momentum to Rapier.
      const overspeedBrake = clamp((forwardSpeed - topSpeed) / tuning.governorBand, 0, 1);
      const serviceBrake = brakeForce * Math.max(brake, overspeedBrake) / wheelCount;
      // Reverse is a gentle push backwards, only when throttle is released and the car is nearly stopped or already reversing.
      const backing = throttle === 0 && forwardSpeed < 1 ? reverse * clamp((REVERSE_TOP_SPEED + forwardSpeed) / tuning.governorBand, 0, 1) : 0;
      const drive = (engineForce * tuning.gears[gear - 1].multiplier * throttle * speedScale - engineForce * 0.5 * backing) / axleSize;

      for (let index = 0; index < wheelCount; index++) {
        const rear = index >= axleSize;
        const lock = rear ? handbrake : 0;
        const parkingBrake = brakeForce * tuning.handbrakeMultiplier * lock / axleSize;
        const wheelBrake = Math.max(serviceBrake, parkingBrake);
        controller.setWheelSteering(index, rear ? 0 : steering);
        controller.setWheelEngineForce(index, upright && rear && wheelBrake === 0 ? drive : 0);
        controller.setWheelBrake(index, upright ? wheelBrake * dt : 0);
        controller.setWheelFrictionSlip(index, tuning.frictionSlip + lock * (tuning.handbrakeSlip - tuning.frictionSlip));
        controller.setWheelSideFrictionStiffness(index, tuning.sideFriction + lock * (tuning.handbrakeSideFriction - tuning.sideFriction));
      }

      const rollBeforeWheels = bike && upright ? dot(body.angvel(), direction) : 0;
      controller.updateVehicle(dt, WHEEL_FILTER);
      if (upright) stabilizeRoll(dt, rotation, direction, speed, steering, rollBeforeWheels);
    },

    /** Speed is horizontal in m/s. Bike roll is already included in the body quaternion. */
    getState() {
      const quaternion = body.rotation();
      const velocity = body.linvel();
      const direction = forward(quaternion);
      const wheels = Array.from({ length: wheelCount }, (_, index) => ({
        rotation: controller.wheelRotation(index),
        steering: controller.wheelSteering(index),
        suspensionLength: controller.wheelSuspensionLength(index),
        grounded: controller.wheelIsInContact(index),
      }));
      return {
        position: body.translation(),
        quaternion,
        heading: Math.atan2(direction.x, direction.z),
        speed: Math.hypot(velocity.x, velocity.z),
        forwardSpeed: dot(direction, velocity),
        gear, wheels,
        leanAngle: bike ? bikeRoll(quaternion) : 0,
        damage: crash.damage,
        flipped: crash.flipped,
      };
    },

    /** By default keep the location and yaw, lifting a fallen chassis enough to right it. */
    resetUpright({ position: target, heading: yaw, repair = false } = {}) {
      const current = this.getState();
      const lift = upDot(current.quaternion) < 0.9 ? spawnHeight : 0;
      crash.reset({
        position: target ?? { ...current.position, y: current.position.y + lift },
        heading: yaw ?? current.heading,
        repair,
      });
      controls = neutral;
      gear = 1;
      world.removeVehicleController(controller);
      controller = makeController();
    },

    dispose() {
      world.removeVehicleController(controller);
      world.removeRigidBody(body);
    },
  };
}

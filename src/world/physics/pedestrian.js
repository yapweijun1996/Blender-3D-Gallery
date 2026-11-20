import RAPIER from "@dimforge/rapier3d-compat";

export const PEDESTRIAN_TUNING = Object.freeze({
  radius: 0.32,
  height: 1.75,
  offset: 0.02,
  stepHeight: 0.25,
  stepWidth: 0.20,
  snapDistance: 0.20,
});

export function createPedestrian(world, {
  radius = PEDESTRIAN_TUNING.radius,
  height = PEDESTRIAN_TUNING.height,
  offset = PEDESTRIAN_TUNING.offset,
  position = { x: 0, y: height / 2 + offset, z: 0 },
} = {}) {
  if (!(radius > 0 && height >= 2 * radius && offset > 0)
    || ![radius, height, offset].every(Number.isFinite)) {
    throw new RangeError("Expected a positive capsule radius and offset, and height at least twice the radius");
  }
  // Position is the capsule center. Rapier's capsule half-height excludes the end caps.
  const body = world.createRigidBody(RAPIER.RigidBodyDesc.kinematicPositionBased()
    .setTranslation(position.x, position.y, position.z));
  const collider = world.createCollider(RAPIER.ColliderDesc.capsule(height / 2 - radius, radius), body);
  const controller = world.createCharacterController(offset);
  controller.enableAutostep(PEDESTRIAN_TUNING.stepHeight, PEDESTRIAN_TUNING.stepWidth, false);
  controller.enableSnapToGround(PEDESTRIAN_TUNING.snapDistance);

  let x = 0;
  let z = 0;
  let verticalSpeed = 0;
  let grounded = false;

  return {
    body, collider,

    /** Desired horizontal velocity in m/s. The helper integrates vertical gravity. */
    setVelocity(velocity) {
      x = Number.isFinite(velocity.x) ? velocity.x : 0;
      z = Number.isFinite(velocity.z) ? velocity.z : 0;
    },

    update(dt) {
      verticalSpeed += world.gravity.y * dt;
      const desiredY = verticalSpeed * dt;
      controller.computeColliderMovement(collider, { x: x * dt, y: desiredY, z: z * dt },
        RAPIER.QueryFilterFlags.EXCLUDE_SENSORS);
      const movement = controller.computedMovement();
      const current = body.translation();
      grounded = controller.computedGrounded();
      if (grounded && verticalSpeed < 0) verticalSpeed = 0;
      body.setNextKinematicTranslation({
        x: current.x + movement.x,
        y: current.y + movement.y,
        z: current.z + movement.z,
      });
    },

    getState() {
      return { position: body.translation(), grounded };
    },

    dispose() {
      world.removeCharacterController(controller);
      world.removeRigidBody(body);
    },
  };
}

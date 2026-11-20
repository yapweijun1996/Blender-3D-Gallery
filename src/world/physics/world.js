import RAPIER from "@dimforge/rapier3d-compat";
import { drainCrashEvents } from "./crash.js";
import { createPedestrian } from "./pedestrian.js";
import { createVehicle } from "./vehicle.js";

export const FIXED_DT = 1 / 60;
export const MAX_SUBSTEPS = 5;
const ORIGIN = { x: 0, y: 0, z: 0 };
const ROUNDING_TOLERANCE = 1e-12;
let initialization;

export async function createPhysicsWorld({ gravity = { x: 0, y: -9.81, z: 0 } } = {}) {
  initialization ??= RAPIER.init().catch((error) => {
    initialization = undefined;
    throw error;
  });
  await initialization;

  const world = new RAPIER.World(gravity);
  world.timestep = FIXED_DT;
  const events = new RAPIER.EventQueue(true);
  const vehicles = new Map();
  const pedestrians = new Map();
  const statics = new Set();
  const crashes = new Map();
  let accumulator = 0;
  let disposed = false;

  function assertActive() {
    if (disposed) throw new Error("Physics world is disposed");
  }

  function addStatic(desc, { position = ORIGIN, rotation, friction = 0.8 } = {}) {
    desc.setTranslation(position.x, position.y, position.z).setFriction(friction);
    if (rotation) desc.setRotation(rotation);
    const collider = world.createCollider(desc);
    statics.add(collider);
    return collider;
  }

  return {
    /** Raw Rapier world for scene queries. Advance the simulation through this wrapper's step(). */
    world,

    /** Advances by frame seconds and returns the completed fixed steps and render blend. */
    step(frameSeconds) {
      assertActive();
      if (!Number.isFinite(frameSeconds) || frameSeconds < 0) {
        throw new RangeError("Expected a finite, nonnegative frame duration in seconds");
      }
      // Bound catch-up work and preserve the fractional time carried from the previous frame.
      accumulator += Math.min(frameSeconds, MAX_SUBSTEPS * FIXED_DT);
      const substeps = Math.min(MAX_SUBSTEPS, Math.floor((accumulator + ROUNDING_TOLERANCE) / FIXED_DT));
      for (let step = 0; step < substeps; step++) {
        for (const pedestrian of pedestrians.values()) pedestrian.update(FIXED_DT);
        for (const vehicle of vehicles.values()) vehicle.update(FIXED_DT);
        world.step(events);
        drainCrashEvents(events, FIXED_DT, crashes);
        for (const vehicle of vehicles.values()) vehicle.crash.step(FIXED_DT);
      }
      accumulator = Math.max(0, accumulator - substeps * FIXED_DT);
      return { substeps, alpha: accumulator / FIXED_DT };
    },

    addStaticBox({ halfExtents, ...options }) {
      assertActive();
      return addStatic(RAPIER.ColliderDesc.cuboid(halfExtents.x, halfExtents.y, halfExtents.z), options);
    },

    /** Vertices are XYZ triples, indices are triangle triples and both are local to the collider. */
    addStaticTrimesh({ vertices, indices, ...options }) {
      assertActive();
      const vertexBuffer = vertices instanceof Float32Array ? vertices : new Float32Array(vertices);
      const indexBuffer = indices instanceof Uint32Array ? indices : new Uint32Array(indices);
      return addStatic(RAPIER.ColliderDesc.trimesh(vertexBuffer, indexBuffer, RAPIER.TriMeshFlags.FIX_INTERNAL_EDGES), options);
    },

    /** Flat, finite ground tile whose top face lies at height. All dimensions are in meters. */
    addGround({ x = 0, z = 0, height = 0, halfWidth = 500, halfDepth = 500, thickness = 1, friction } = {}) {
      assertActive();
      return addStatic(RAPIER.ColliderDesc.cuboid(halfWidth, thickness / 2, halfDepth), {
        position: { x, y: height - thickness / 2, z }, friction,
      });
    },

    /** A box moved by the game (traffic): other bodies collide with it, but it never reacts. Poses are set every frame. */
    addKinematicBox({ halfExtents, position = ORIGIN, yaw = 0 }) {
      assertActive();
      const body = world.createRigidBody(RAPIER.RigidBodyDesc.kinematicPositionBased()
        .setTranslation(position.x, position.y, position.z).setRotation({ x: 0, y: Math.sin(yaw / 2), z: 0, w: Math.cos(yaw / 2) }));
      const collider = world.createCollider(RAPIER.ColliderDesc.cuboid(halfExtents.x, halfExtents.y, halfExtents.z).setFriction(0.4), body);
      return {
        collider,
        setPose(x, y, z, heading) {
          body.setNextKinematicTranslation({ x, y, z });
          body.setNextKinematicRotation({ x: 0, y: Math.sin(heading / 2), z: 0, w: Math.cos(heading / 2) });
        },
        remove() { if (!disposed) world.removeRigidBody(body); },
      };
    },

    removeStatic(collider) {
      assertActive();
      if (statics.delete(collider)) world.removeCollider(collider, true);
    },

    addVehicle(options) {
      assertActive();
      const { update, crash, dispose, ...vehicle } = createVehicle(world, options);
      vehicles.set(vehicle, { update, crash, dispose });
      crashes.set(vehicle.collider.handle, crash);
      return vehicle;
    },

    removeVehicle(vehicle) {
      assertActive();
      const registration = vehicles.get(vehicle);
      if (!registration) return;
      vehicles.delete(vehicle);
      crashes.delete(vehicle.collider.handle);
      registration.dispose();
    },

    addPedestrian(options) {
      assertActive();
      const { update, dispose, ...pedestrian } = createPedestrian(world, options);
      pedestrians.set(pedestrian, { update, dispose });
      return pedestrian;
    },

    removePedestrian(pedestrian) {
      assertActive();
      const registration = pedestrians.get(pedestrian);
      if (!registration) return;
      pedestrians.delete(pedestrian);
      registration.dispose();
    },

    dispose() {
      if (disposed) return;
      disposed = true;
      for (const vehicle of vehicles.values()) vehicle.dispose();
      for (const pedestrian of pedestrians.values()) pedestrian.dispose();
      vehicles.clear();
      pedestrians.clear();
      statics.clear();
      crashes.clear();
      events.free();
      world.free();
    },
  };
}

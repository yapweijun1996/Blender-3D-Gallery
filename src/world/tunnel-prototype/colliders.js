/** Install the triangles used to render the prototype as static Rapier colliders. */
export function installTunnelColliders(physics, surfaces) {
  const colliders = [];

  function dispose() {
    for (const collider of colliders.splice(0).reverse()) physics.removeStatic(collider);
  }

  try {
    for (const { position, indices } of surfaces) {
      colliders.push(physics.addStaticTrimesh({ vertices: position, indices, friction: 1 }));
    }
  } catch (error) {
    dispose();
    throw error;
  }

  return dispose;
}

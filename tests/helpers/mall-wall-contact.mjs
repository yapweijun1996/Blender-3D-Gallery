import { Raycaster, Vector3 } from 'three';
import { measureCorridor } from './mall-mesh.mjs';

// Preserve the shared floor checks. A vertical ray can miss a coplanar shared edge.
export async function measureWallContact(root) {
  const scene = await measureCorridor(root);
  const floors = root.children.filter(part => part.userData.moduleId === 'floor' || part.userData.moduleId === 'floor2m');
  const ray = new Raycaster(new Vector3(), new Vector3(0, -1, 0), 0, .5);
  const corrections = { count: 0, maxDistanceMetres: 0 };
  function supportedHeight(x, z) {
    const y = scene.surface(x, z);
    if (y !== null && y >= -.001001) return y;
    ray.ray.origin.set(x, .1, z);
    const hit = ray.intersectObjects(floors, true)[0];
    if (!hit || (y !== null && hit.point.y <= y + .000001)) return y;
    // Same x/z, no shifted or averaged probes. The closest point on the float32
    // Rapier triangles must match the double-precision hit in all three axes.
    const nearest = scene.projectFloor(hit.point);
    if (!nearest) return y;
    const distance = hit.point.distanceTo(nearest);
    if (distance > .000001) return y;
    corrections.count++;
    corrections.maxDistanceMetres = Math.max(corrections.maxDistanceMetres, distance);
    return nearest.y;
  }
  return { ...scene, rawSurface: scene.surface, surface: supportedHeight, corrections };
}

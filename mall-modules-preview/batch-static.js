import { Mesh } from 'three';
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js';

// Preserve the individual placed roots for collision, door articulation and
// inspection. Only the assembly draws batched copies of its fixed opaque faces.
export function batchStaticMeshes(group) {
  const batches = new Map();
  group.updateWorldMatrix(true, true);
  const inverseRoot = group.matrixWorld.clone().invert();
  for (const module of group.children) {
    if (module.userData.moduleId === 'door') continue;
    module.traverseVisible(mesh => {
      if (!mesh.isMesh || Array.isArray(mesh.material) || mesh.material.transparent ||
          mesh.isSkinnedMesh || mesh.matrixWorld.determinant() < 0) return;
      const signature = Object.entries(mesh.geometry.attributes).sort(([a], [b]) => a.localeCompare(b))
        .map(([key, a]) => [key, a.itemSize, a.normalized, a.array.constructor.name].join('/')).join(',');
      const key = mesh.material.uuid + signature;
      if (!batches.has(key)) batches.set(key, []);
      batches.get(key).push(mesh);
    });
  }
  for (const meshes of batches.values()) {
    if (meshes.length < 2) continue;
    const parts = meshes.map(mesh => {
      const geometry = mesh.geometry.index ? mesh.geometry.toNonIndexed() : mesh.geometry.clone();
      return geometry.applyMatrix4(inverseRoot.clone().multiply(mesh.matrixWorld));
    });
    const merged = mergeGeometries(parts);
    for (const part of parts) part.dispose();
    if (!merged) throw new Error('Unable to batch static corridor geometry');
    const batch = new Mesh(merged, meshes[0].material);
    group.add(batch);
    for (const mesh of meshes) mesh.visible = false;
  }
}

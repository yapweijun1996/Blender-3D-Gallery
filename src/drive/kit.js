import { Box3, Color, InstancedMesh, Matrix4, Quaternion, Vector3 } from "three";
import { loadModels } from "../chibi-dressup/view.js";

// Model kits built in Blender (models/drive/kit/*.glb): vehicles, street furniture, trees, buildings, landmarks.
const urls = import.meta.glob("../../models/drive/kit/*.glb", { eager: true, query: "?url", import: "default" });

/** Materials whose colour may be tinted per instance (the others keep the colours the model was built with). */
const TINTABLE = new Set(["paint", "wall", "roof"]);

export const KIT_NAMES = [
  "car_hatchback", "car_sedan", "bus", "motorbike", "street_lamp", "traffic_light", "sign_gantry", "bus_stop", "guardrail", "road_cone",
  "tree_raintree", "tree_palm", "tree_street", "shrub_hedge",
  "building_hdb", "building_tower_glass", "building_shophouse", "building_condo", "building_lowrise",
  "landmark_mbs", "landmark_checkpoint", "landmark_southkey",
];

/** Load the whole kit; a missing file only drops that model, so the world falls back to simple shapes for it. */
export async function loadKit(signal, scenes = new Set()) {
  const entries = KIT_NAMES.map(name => [name, urls[`../../models/drive/kit/${name}.glb`]]).filter(([, url]) => url);
  const loaded = await Promise.allSettled(entries.map(([, url]) => loadModels([url], signal, scenes).then(([gltf]) => gltf)));
  signal?.throwIfAborted();
  const kit = new Map();
  entries.forEach(([name], index) => {
    const result = loaded[index];
    if (result.status !== "fulfilled") { console.error(`Drive: kit model ${name} failed to load`, result.reason); return; }
    const scene = result.value.scene;
    scene.updateMatrixWorld(true);
    const box = new Box3().setFromObject(scene);
    const size = box.getSize(new Vector3());
    const parts = [];
    scene.traverse(node => {
      if (!node.isMesh) return;
      parts.push({ name: node.name, geometry: node.geometry, material: node.material, matrix: node.matrixWorld.clone() });
    });
    kit.set(name, { name, scene, parts, size, box });
  });
  return kit;
}

const matrix = new Matrix4(), quaternion = new Quaternion(), up = new Vector3(0, 1, 0), position = new Vector3(), scale = new Vector3();

/**
 * One InstancedMesh per part of a model. A placement is { x, y, z, yaw, scale, sx, sy, sz, color }.
 * `color` tints only the paint, wall and roof materials. Returns the meshes and a function that rewrites the matrices.
 */
export function instanceModel(model, placements, { dynamic = false } = {}) {
  const meshes = model.parts.map(part => {
    const materials = [part.material].flat();
    const tint = materials.some(material => TINTABLE.has(material.name));
    const mesh = new InstancedMesh(part.geometry, part.material, Math.max(1, placements.length));
    mesh.frustumCulled = false;
    mesh.userData.tint = tint;
    mesh.userData.part = part;
    return mesh;
  });
  const color = new Color();
  function write(list) {
    for (const mesh of meshes) {
      const { part, tint } = { part: mesh.userData.part, tint: mesh.userData.tint };
      mesh.count = list.length;
      list.forEach((placement, index) => {
        quaternion.setFromAxisAngle(up, placement.yaw ?? 0);
        const uniform = placement.scale ?? 1;
        scale.set(placement.sx ?? uniform, placement.sy ?? uniform, placement.sz ?? uniform);
        position.set(placement.x, placement.y ?? 0, placement.z);
        matrix.compose(position, quaternion, scale).multiply(part.matrix);
        mesh.setMatrixAt(index, matrix);
        if (tint && placement.color !== undefined) mesh.setColorAt(index, color.set(placement.color));
      });
      mesh.instanceMatrix.needsUpdate = true;
      if (mesh.instanceColor) mesh.instanceColor.needsUpdate = true;
      if (dynamic) mesh.instanceMatrix.setUsage(35048); // DynamicDrawUsage
    }
  }
  write(placements);
  return { meshes, write };
}

/** Plain, non-instanced copy of a model with its paint recoloured (for the player's car). */
export function cloneModel(model, paintColor) {
  const copy = model.scene.clone(true);
  copy.traverse(node => {
    if (!node.isMesh) return;
    node.material = [node.material].flat().map(material => {
      if (material.name !== "paint" || paintColor === undefined) return material;
      const tinted = material.clone();
      tinted.color.set(paintColor);
      return tinted;
    });
    if (node.material.length === 1) node.material = node.material[0];
  });
  return copy;
}

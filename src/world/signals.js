import { BoxGeometry, Color, CylinderGeometry, InstancedMesh, Matrix4, MeshBasicMaterial, MeshLambertMaterial, Quaternion, SphereGeometry, Vector3 } from "three";
import { sampleEdge, phaseOf } from "./traffic.js";

// Traffic lights drawn at the signalised junctions: a pole and a three-lamp head on the left verge of every approach,
// facing the oncoming vehicles. Lamps are one instanced mesh whose per-instance colour follows the signal state.
const COLORS = { red: new Color(0xff3b30), amber: new Color(0xffb020), green: new Color(0x2ee66b), off: new Color(0x2b2b2b) };
const LAMP_ORDER = ["red", "amber", "green"]; // top to bottom
const STOP_LINE = 6;       // metres before the junction
const POLE_HEIGHT = 5;

/** The approaches of signalised junctions in a traffic graph: { x, z, dx, dz, phase } with (dx, dz) the direction of travel. */
export function signalApproaches(graph) {
  const approaches = [];
  for (const nodeId of graph.signalised) {
    const node = graph.nodes.get(nodeId);
    if (!node) continue;
    const arrive = [];
    for (const id of node.backward) arrive.push({ edge: graph.edges.get(id), direction: 1 });
    for (const id of node.forward) { const edge = graph.edges.get(id); if (edge && !edge.oneway) arrive.push({ edge, direction: -1 }); }
    for (const { edge, direction } of arrive) {
      if (!edge || edge.length < STOP_LINE * 2) continue;
      const at = sampleEdge(edge, edge.length - STOP_LINE, direction);
      const side = edge.width / 2 + 1.4; // the left verge of the approach: left of travel is (dz, -dx)
      approaches.push({ x: at.x + at.dz * side, z: at.z - at.dx * side, dx: at.dx, dz: at.dz, phase: phaseOf(at.dx, at.dz) });
    }
  }
  return approaches;
}

export function createSignalLights(scene, capacity = 96) {
  const poleMaterial = new MeshLambertMaterial({ color: 0x8c9096 }), headMaterial = new MeshLambertMaterial({ color: 0x1d1f22 }), lampMaterial = new MeshBasicMaterial({ color: 0xffffff });
  const poles = new InstancedMesh(new CylinderGeometry(0.09, 0.11, POLE_HEIGHT, 8), poleMaterial, capacity);
  const heads = new InstancedMesh(new BoxGeometry(0.42, 1.15, 0.36), headMaterial, capacity);
  const lamps = new InstancedMesh(new SphereGeometry(0.14, 10, 8), lampMaterial, capacity * 3);
  for (const mesh of [poles, heads, lamps]) { mesh.frustumCulled = false; mesh.count = 0; scene.add(mesh); }
  let current = [];
  const matrix = new Matrix4(), base = new Matrix4(), local = new Matrix4(), quaternion = new Quaternion(), up = new Vector3(0, 1, 0), unit = new Vector3(1, 1, 1);

  return {
    meshes: [poles, heads, lamps],
    get count() { return current.length; },
    /** Place the poles; `near` limits them to a radius around a point so only the junctions around the player are drawn. */
    setApproaches(list, near, radius = 450) {
      current = list.filter(item => !near || Math.hypot(item.x - near.x, item.z - near.z) < radius).slice(0, capacity);
      poles.count = heads.count = current.length;
      lamps.count = current.length * 3;
      current.forEach((item, index) => {
        // Face the oncoming vehicles: opposite to the direction of travel.
        quaternion.setFromAxisAngle(up, Math.atan2(-item.dx, -item.dz));
        base.compose(new Vector3(item.x, 0, item.z), quaternion, unit);
        poles.setMatrixAt(index, matrix.copy(base).multiply(local.makeTranslation(0, POLE_HEIGHT / 2, 0)));
        heads.setMatrixAt(index, matrix.copy(base).multiply(local.makeTranslation(0, POLE_HEIGHT + 0.4, 0)));
        LAMP_ORDER.forEach((_, lamp) => lamps.setMatrixAt(index * 3 + lamp, matrix.copy(base).multiply(local.makeTranslation(0, POLE_HEIGHT + 0.4 + 0.36 - lamp * 0.36, 0.2))));
      });
      for (const mesh of [poles, heads, lamps]) mesh.instanceMatrix.needsUpdate = true;
    },
    /** Light the lamp that matches each approach's state. `stateOf(dx, dz)` returns "green", "amber" or "red". */
    update(stateOf) {
      current.forEach((item, index) => {
        const state = stateOf(item.dx, item.dz);
        LAMP_ORDER.forEach((name, lamp) => lamps.setColorAt(index * 3 + lamp, name === state ? COLORS[name] : COLORS.off));
      });
      if (lamps.instanceColor) lamps.instanceColor.needsUpdate = true;
    },
    dispose() {
      for (const mesh of [poles, heads, lamps]) { scene.remove(mesh); mesh.geometry.dispose(); mesh.material.dispose(); mesh.dispose(); }
    },
  };
}
